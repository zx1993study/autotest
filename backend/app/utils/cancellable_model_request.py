"""Keep unlimited model I/O interruptible without leaving blocked worker threads."""
from __future__ import annotations

import multiprocessing
from collections.abc import Callable
from urllib import error, request

from app.utils.model_api_response import ModelResponseError, read_model_response


class ModelRequestCancelled(RuntimeError):
    pass


def _receive_model(sender, url, headers, body, protocol):
    try:
        req = request.Request(url, data=body, headers=headers, method="POST")
        with request.urlopen(req, timeout=None) as response:
            value = read_model_response(response, protocol, timeout_sec=None)
        sender.send(("ok", value))
    except error.HTTPError as exc:
        sender.send(("http", exc.code, dict(exc.headers), exc.read(501).decode("utf-8", errors="replace")))
    except error.URLError as exc:
        sender.send(("connection", str(exc.reason)))
    except Exception as exc:  # noqa: BLE001 - exceptions cross the process boundary as plain data.
        sender.send(("invalid", str(exc)))
    finally:
        sender.close()


def cancellable_model_response(req, protocol: str, cancelled: Callable[[], bool] | None):
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_receive_model, args=(sender, req.full_url, dict(req.header_items()), req.data, protocol), daemon=True)
    try:
        process.start()
        sender.close()
        while not receiver.poll(0.25):
            if cancelled and cancelled():
                raise ModelRequestCancelled("用户已中止 AI 分析")
            if not process.is_alive():
                raise ModelResponseError("Model request worker stopped without a response")
        if cancelled and cancelled():
            raise ModelRequestCancelled("用户已中止 AI 分析")
        value = receiver.recv()
        if value[0] == "ok":
            return value[1]
        if value[0] == "http":
            import io

            raise error.HTTPError(req.full_url, value[1], "Model HTTP error", value[2], io.BytesIO(value[3].encode("utf-8")))
        if value[0] == "connection":
            raise error.URLError(value[1])
        raise ModelResponseError(value[1])
    finally:
        receiver.close()
        sender.close()
        if process.pid:
            if process.is_alive():
                process.terminate()
            process.join()
