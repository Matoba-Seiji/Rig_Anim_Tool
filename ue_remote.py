import json
import os
import socket
import struct
import sys
import time
import uuid


UE_MULTICAST_GROUP = ('239.0.0.1', 6766)
UE_MULTICAST_TTL = 1
UE_MULTICAST_IFACE = '127.0.0.1'
UE_PROTOCOL_VERSION = 1
UE_PROTOCOL_MAGIC = 'ue_py'

UE_PLUGIN_REMOTE_EXEC_DIRS = [
    r'C:\Program Files\Epic Games\UE_5.5\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python',
    r'C:\Program Files\Epic Games\UE_5.4\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python',
    r'C:\Program Files\Epic Games\UE_5.3\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python',
]

_UE_RE = None


def _try_import_ue_remote_execution():
    for d in UE_PLUGIN_REMOTE_EXEC_DIRS:
        if os.path.isfile(os.path.join(d, 'remote_execution.py')):
            if d not in sys.path:
                sys.path.insert(0, d)
            try:
                import remote_execution as _re
                return _re
            except Exception:
                continue
    return None


def _ue_exec_mode_value(exec_mode):
    if not _UE_RE:
        return exec_mode
    mode_attrs = {
        'ExecuteFile': 'MODE_EXEC_FILE',
        'ExecuteStatement': 'MODE_EXEC_STATEMENT',
        'EvaluateStatement': 'MODE_EVAL_STATEMENT',
    }
    return getattr(_UE_RE, mode_attrs.get(exec_mode, ''), exec_mode)


def _ue_make_node_id():
    return str(uuid.uuid4())


def _ue_make_message(msg_type, source, dest=None, data=None):
    msg = {
        'version': UE_PROTOCOL_VERSION,
        'magic': UE_PROTOCOL_MAGIC,
        'source': source,
        'type': msg_type,
    }
    if dest is not None:
        msg['dest'] = dest
    if data is not None:
        msg['data'] = data
    return json.dumps(msg).encode('utf-8')


def _ue_make_sockets():
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
    send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL,
                         struct.pack('b', UE_MULTICAST_TTL))
    send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                         socket.inet_aton(UE_MULTICAST_IFACE))

    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    recv_sock.bind((UE_MULTICAST_IFACE, 0))
    mreq = struct.pack('=4s4s', socket.inet_aton(UE_MULTICAST_GROUP[0]),
                       socket.inet_aton(UE_MULTICAST_IFACE))
    recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return send_sock, recv_sock


def _ue_send(send_sock, payload):
    try:
        send_sock.sendto(payload, UE_MULTICAST_GROUP)
    except OSError:
        pass
    try:
        send_sock.sendto(payload, (UE_MULTICAST_IFACE, UE_MULTICAST_GROUP[1]))
    except OSError:
        pass


def ue_discover_nodes(timeout=1.0):
    global _UE_RE
    if _UE_RE is None:
        _UE_RE = _try_import_ue_remote_execution() or False

    if _UE_RE:
        try:
            client = _UE_RE.RemoteExecution()
            client.start()
            time.sleep(timeout)
            nodes_info = list(client.remote_nodes)
            client.stop()
            ids = []
            for n in nodes_info:
                if isinstance(n, dict):
                    nid = n.get('node_id') or n.get('source')
                    if nid:
                        ids.append(nid)
                else:
                    nid = getattr(n, 'node_id', None) or getattr(n, 'source', None)
                    if nid:
                        ids.append(nid)
            return ids
        except Exception:
            return []

    source = _ue_make_node_id()
    send_sock, recv_sock = _ue_make_sockets()
    recv_sock.settimeout(0.2)
    try:
        ping = _ue_make_message('ping', source)
        _ue_send(send_sock, ping)

        nodes = set()
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data, _ = recv_sock.recvfrom(8192)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                msg = json.loads(data.decode('utf-8'))
            except Exception:
                continue
            if msg.get('magic') != UE_PROTOCOL_MAGIC:
                continue
            if msg.get('type') == 'pong' and msg.get('source'):
                nodes.add(msg['source'])
        return list(nodes)
    finally:
        send_sock.close()
        recv_sock.close()


def ue_exec_command(node_id, py_code, exec_mode='ExecuteFile', timeout=30.0,
                    progress_callback=None):
    global _UE_RE
    if _UE_RE is None:
        _UE_RE = _try_import_ue_remote_execution() or False

    if _UE_RE:
        try:
            client = _UE_RE.RemoteExecution()
            client.start()
            wait_deadline = time.time() + 3.0
            while time.time() < wait_deadline:
                if client.remote_nodes:
                    break
                time.sleep(0.2)
            if not client.remote_nodes:
                client.stop()
                return {'success': False, 'result': 'no UE node visible to official client'}
            n0 = client.remote_nodes[0]
            if isinstance(n0, dict):
                target_id = n0.get('node_id') or n0.get('source')
            else:
                target_id = getattr(n0, 'node_id', None) or getattr(n0, 'source', None)
            try:
                client.open_command_connection(target_id)
            except Exception:
                pass
            start = time.time()
            try:
                result = client.run_command(py_code, unattended=True,
                                            exec_mode=_ue_exec_mode_value(exec_mode),
                                            raise_on_failure=False)
            finally:
                try:
                    client.close_command_connection()
                except Exception:
                    pass
                client.stop()
            if progress_callback:
                try:
                    progress_callback(time.time() - start)
                except Exception:
                    pass
            return result if isinstance(result, dict) else {
                'success': True, 'result': str(result)}
        except Exception as e:
            return {'success': False, 'result': f'official client exception: {e}'}

    source = _ue_make_node_id()
    send_sock, recv_sock = _ue_make_sockets()
    recv_sock.settimeout(0.3)
    try:
        cmd_msg = _ue_make_message(
            'command', source, dest=node_id,
            data={'command': py_code, 'unattended': True, 'exec_mode': exec_mode},
        )
        _ue_send(send_sock, cmd_msg)

        start = time.time()
        deadline = start + timeout
        while time.time() < deadline:
            try:
                data, _ = recv_sock.recvfrom(65535)
            except socket.timeout:
                if progress_callback:
                    try:
                        progress_callback(time.time() - start)
                    except Exception:
                        pass
                continue
            except OSError:
                break
            try:
                msg = json.loads(data.decode('utf-8'))
            except Exception:
                continue
            if msg.get('magic') != UE_PROTOCOL_MAGIC:
                continue
            if msg.get('type') == 'command_result' and msg.get('dest') == source:
                return msg.get('data', {})
        return {'success': False, 'result': 'timeout waiting for UE response'}
    finally:
        send_sock.close()
        recv_sock.close()
