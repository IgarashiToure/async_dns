#!/usr/bin/env python
# coding=utf-8
import asyncio

connections = {}

class CallbackProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        self.cached = True
        self._close_handle = None
        self.reset_close()
        self.set_future()

    def set_future(self, future = None):
        self.future = future
        transport = self.transport
        if future is None:
            transport.pause_reading()
            # transport.pause_writing()
        else:
            transport.resume_reading()
            # transport.resume_writing()

    def write_data(self, future, data):
        self.reset_close()
        self.set_future(future)
        self.transport.write(data)

    def data_received(self, data):
        if self.future is not None:
            if not self.future.cancelled():
                self.future.set_result(data)
            self.set_future()

    def reset_close(self):
        if self._close_handle:
            self._close_handle.cancel()
        loop = asyncio.get_event_loop()
        self._close_handle = loop.call_later(120, self._close)

    def _close(self):
        connections.pop(self.key, None)
        self.cached = False
        self.transport.close()

    def connection_lost(self, exc):
        if self.cached:
            self._close()

async def request(qdata, addr, timeout = 3.0):
    key = addr.to_str(53)
    protocol = connections.get(key)
    if protocol is None:
        loop = asyncio.get_event_loop()
        transport, protocol = await asyncio.wait_for(
            loop.create_connection(CallbackProtocol, host=addr.hostname, port=addr.port),
            1.0
        )
        connections[key] = protocol
        protocol.key = key
    future = asyncio.Future()
    protocol.write_data(future, qdata)
    data = await asyncio.wait_for(future, timeout)
    return data
