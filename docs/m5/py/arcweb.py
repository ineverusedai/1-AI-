"""브라우저(Pyodide) 안에서 ARC-AGI-3 게임을 돌리는 얇은 다리. 공식 toolkit 의 LocalEnvironmentWrapper 와 같은 방식으로
게임 소스를 exec 하고 클래스를 만들어 perform_action 을 부른다."""
import json
import numpy as np
from arcengine import ActionInput, ARCBaseGame, GameAction

GAMES = {}


def load(gid, class_name, source):
    ns = {"__name__": f"arc_agi_3.{gid}"}
    exec(source, ns)
    cls = ns[class_name]
    assert issubclass(cls, ARCBaseGame)
    GAMES[gid] = cls()


def step(gid, action_id, x=-1, y=-1):
    g = GAMES[gid]
    act = GameAction.from_id(int(action_id))
    data = {"x": int(x), "y": int(y)} if act.is_complex() else {}
    act.validate_data(data)
    fd = g.perform_action(ActionInput(id=act, data=data), raw=True)
    frames = np.stack([np.asarray(f, dtype=np.uint8) for f in fd.frame]) if fd.frame else np.zeros((0, 64, 64), np.uint8)
    meta = {"state": fd.state.value, "levels": fd.levels_completed, "win": fd.win_levels,
            "actions": list(fd.available_actions), "n": int(frames.shape[0]),
            "h": int(frames.shape[1]) if frames.size else 64, "w": int(frames.shape[2]) if frames.size else 64}
    return json.dumps(meta), frames.tobytes()
