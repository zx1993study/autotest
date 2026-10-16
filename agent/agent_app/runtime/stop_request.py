from agent_app.runtime.local_state import runtime_path


def stop_path(config):
    return runtime_path(config.node_key).with_suffix(".stop")


def requested(config):
    return stop_path(config).exists()


def request(config):
    path = stop_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def clear(config):
    stop_path(config).unlink(missing_ok=True)
