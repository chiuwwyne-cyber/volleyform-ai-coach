import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from action.block import check_block
from action.receive import check_receive
from action.serve import check_serve
from action.set import check_set
from action.spike import check_spike
from backend.feedback import ACTION_LABELS


def _spike(angles, positions=None, hand_features=None):
    return check_spike(angles)


def _block(angles, positions=None, hand_features=None):
    return check_block(angles)


def _serve(angles, positions=None, hand_features=None):
    return check_serve(angles)


def _receive(angles, positions=None, hand_features=None):
    return check_receive(angles, positions, hand_features)


def _set(angles, positions=None, hand_features=None):
    return check_set(angles, positions, hand_features)


ACTION_CHECKERS = {
    "spike": _spike,
    "block": _block,
    "serve": _serve,
    "receive": _receive,
    "set": _set,
}


def available_actions():
    return sorted(ACTION_CHECKERS.keys())


def available_action_options():
    return [
        {
            "id": action_id,
            "label": ACTION_LABELS.get(action_id, action_id),
        }
        for action_id in available_actions()
    ]


def check_action(action_type, angles, positions=None, hand_features=None):
    checker = ACTION_CHECKERS.get(action_type)
    if checker is None:
        return ["unknown_action"]
    return checker(angles, positions, hand_features)
