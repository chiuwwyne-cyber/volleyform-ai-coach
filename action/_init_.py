from .spike import check_spike
from .receive import check_receive
from .block import check_block
from .serve import check_serve
from .set import check_set

def check_action(action_type, angles, positions=None):

    if action_type == "spike":
        return check_spike(angles)

    elif action_type == "receive":
        return check_receive(angles)

    elif action_type == "block":
        return check_block(angles)

    elif action_type == "serve":
        return check_serve(angles)

    elif action_type == "set":
        return check_set(angles, positions)

    else:
        return ["unknown_action"]