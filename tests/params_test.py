import pytest

from remote_params import FloatParam, IntParam, Param, Params


class TestParams:
    def test_string(self):
        params = Params()
        param = params.string("name")
        assert param.type == "s"
        assert isinstance(param, Param)

        param.set(4)
        assert param.get() == "4"

    def test_int(self):
        params = Params()
        param = params.int("age")
        assert param.type == "i"
        assert isinstance(param, Param)

        param.set("4")
        assert param.get() == 4
        with pytest.raises(ValueError):
            param.set("zzz")

    def test_bool(self):
        params = Params()
        param = params.bool("checked")
        assert param.type == "b"
        assert isinstance(param, Param)

        param.set("true")
        assert param.get()
        assert param.on_change._fireCount == 1

        param.set("xxx")  # will not change the value
        assert param.get()
        assert param.on_change._fireCount == 1

        param.set("false")
        assert not param.get()
        assert param.on_change._fireCount == 2

        param.set("yyy")  # will not change the value
        assert param.get()
        assert param.on_change._fireCount == 3

    def test_float(self):
        params = Params()
        param = params.float("value")
        assert param.type == "f"
        assert isinstance(param, Param)

        param.set("4.81")
        assert param.get() == 4.81
        with pytest.raises(ValueError):
            param.set("zzz")

    def test_void(self):
        p = Params()
        exitparam = p.void("exit")
        assert exitparam.to_dict()["type"] == "v"

        exits = []
        exitparam.on_change += exits.append
        assert len(exits) == 0
        exitparam.set(1)
        assert len(exits) == 1
        exitparam.set("foo")
        assert len(exits) == 2
        exitparam.trigger()
        assert len(exits) == 3

    def test_void_argumentless_callback(self):
        p = Params()
        exitparam = p.void("exit")
        assert exitparam.to_dict()["type"] == "v"

        exits = []

        def func():
            print("func: {}".format(len(exits)))
            exits.append("func")

        exitparam.ontrigger(func)
        assert len(exits) == 0
        exitparam.trigger()
        assert len(exits) == 1
        assert exits[-1] == "func"

    def test_group(self):
        p = Params()
        assert len(p) == 0
        p2 = Params()
        p.group("P2", p2)
        assert len(p) == 1
        assert p.get("P2") == p2

    def test_propagates_param_changes(self):
        p = Params()
        assert p.on_change._fireCount == 0
        name = p.string("name")
        assert p.on_change._fireCount == 1
        name.set("John")
        assert p.on_change._fireCount == 2

    def test_propagates_params_changes(self):
        p = Params()
        assert len(p) == 0
        p2 = Params()
        p.group("P2", p2)
        assert p.on_change._fireCount == 1
        p2.int("foo")
        assert p.on_change._fireCount == 2

    def test_get(self):
        params = Params()
        param = params.bool("check")
        assert params.get("check") == param
        assert params.get("foo") is None

    def test_get_path_with_invalid_path(self):
        pars = Params()
        pars.string("foo")
        assert pars.get_path("/bar") is None

    def test_duplicate_id(self):
        params = Params()
        p = params.string("foo")
        assert p.type == "s"
        assert len(params) == 1
        p = params.int("foo")
        assert p.type == "i"
        assert len(params) == 1


class TestParam:
    def test_opts(self):
        p = Param("s", "", minlength=3)
        assert p.opts == {"minlength": 3}


class TestIntParam:
    def test_set_with_invalid_value(self):
        p = IntParam()
        p.set(4)
        assert p.get() == 4

        with pytest.raises(ValueError):
            p.set("abc")

        assert p.get() == 4

        p.set("05")
        assert p.get() == 5

    def test_to_dict(self):
        p = IntParam(min=5, max=10)
        assert p.to_dict() == {"type": "i", "value": 0, "opts": {"min": 5, "max": 10}}


class TestFloatParam:
    def test_set_with_invalid_value(self):
        p = FloatParam()
        p.set(4.0)
        assert p.get() == 4.0
        with pytest.raises(ValueError):
            p.set("abc")
        assert p.get() == 4.0
        p.set("05")
        assert p.get() == 5.0

    def test_to_dict(self):
        p = IntParam(min=5, max=10)
        assert p.to_dict() == {"type": "i", "value": 0.0, "opts": {"min": 5, "max": 10}}
