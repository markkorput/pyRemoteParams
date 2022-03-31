from remote_params import FloatParam, IntParam, Param, Params


class TestParams:
    def test_string(self):
        params = Params()
        param = params.string("name")
        assert param.type == "s"
        assert isinstance(param, Param)

        param.set(4)
        assert param.val() == "4"

    def test_int(self):
        params = Params()
        param = params.int("age")
        assert param.type == "i"
        assert isinstance(param, Param)

        param.set("4")
        assert param.val() == 4
        param.set("zzz")
        assert param.val() == 4

    def test_bool(self):
        params = Params()
        param = params.bool("checked")
        assert param.type == "b"
        assert isinstance(param, Param)

        param.set("true")
        assert param.val()
        assert param.changeEvent._fireCount == 1

        param.set("xxx")  # will not change the value
        assert param.val()
        assert param.changeEvent._fireCount == 1

        param.set("false")
        assert not param.val()
        assert param.changeEvent._fireCount == 2

        param.set("yyy")  # will not change the value
        assert not param.val()
        assert param.changeEvent._fireCount == 2

    def test_float(self):
        params = Params()
        param = params.float("value")
        assert param.type == "f"
        assert isinstance(param, Param)

        param.set("4.81")
        assert param.val() == 4.81
        param.set("zzz")
        assert param.val() == 4.81

    def test_void(self):
        p = Params()
        exitparam = p.void("exit")
        assert exitparam.to_dict()["type"] == "v"

        exits = []
        exitparam.onchange(exits.append)
        assert len(exits) == 0
        exitparam.set(None)
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
        assert p.changeEvent._fireCount == 0
        name = p.string("name")
        assert p.changeEvent._fireCount == 1
        name.set("John")
        assert p.changeEvent._fireCount == 2

    def test_propagates_params_changes(self):
        p = Params()
        assert len(p) == 0
        p2 = Params()
        p.group("P2", p2)
        assert p.changeEvent._fireCount == 1
        p2.int("foo")
        assert p.changeEvent._fireCount == 2

    def test_get(self):
        params = Params()
        param = params.bool("check")
        assert params.get("check") == param
        assert params.get("foo") is None


class TestParam:
    def test_setter(self):
        p = Param("f", setter=float)
        p.set("5.50")
        assert p.val() == 5.5

    def test_getter(self):
        p = Param("f", getter=float)
        p.set("5.50")
        assert p.value == "5.50"
        assert p.val() == 5.50

    def test_opts(self):
        p = Param("s", opts={"minlength": 3})
        assert p.opts == {"minlength": 3}


class TestIntParam:
    def test_set_with_invalid_value(self):
        p = IntParam()
        p.set(4)
        assert p.val() == 4
        p.set("abc")
        assert p.val() == 4
        p.set("05")
        assert p.val() == 5

    def test_to_dict(self):
        p = IntParam(min=5, max=10)
        assert p.to_dict() == {"type": "i", "opts": {"min": 5, "max": 10}}


class TestFloatParam:
    def test_set_with_invalid_value(self):
        p = FloatParam()
        p.set(4.0)
        assert p.val() == 4.0
        p.set("abc")
        assert p.val() == 4.0
        p.set("05")
        assert p.val() == 5.0

    def test_to_dict(self):
        p = IntParam(min=5, max=10)
        assert p.to_dict() == {"type": "i", "opts": {"min": 5, "max": 10}}
