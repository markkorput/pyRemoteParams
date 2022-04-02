#!/usr/bin/env python
import json

from remote_params import Params, schema


class TestSchema:
    def test_schema_list_empty(self):
        pars = Params()
        assert schema.schema_list(pars) == []

    def test_schema_list(self):
        pars = Params()
        pars.string("name")
        pars.int("count")
        pars.float("price")
        pars.bool("soldout")

        details = Params()
        details.int("page_count")
        details.string("author")
        pars.group("details", details)

        assert schema.schema_list(pars) == [
            {"value": "", "path": "/name", "type": "s"},
            {"value": 0, "path": "/count", "type": "i"},
            {"value": 0.0, "path": "/price", "type": "f"},
            {"value": False, "path": "/soldout", "type": "b"},
            {"value": 0, "path": "/details/page_count", "type": "i"},
            {"value": "", "path": "/details/author", "type": "s"},
        ]

    def test_schema_list_with_values(self):
        pars = Params()
        pars.string("name").set("Moby Dick")
        pars.int("count").set(100)
        pars.float("price").set(9.99)
        pars.bool("soldout").set(False)

        details = Params()
        details.int("page_count").set(345)
        details.string("author").set("Herman Melville")
        pars.group("details", details)

        assert schema.schema_list(pars) == [
            {"path": "/name", "type": "s", "value": "Moby Dick"},
            {"path": "/count", "type": "i", "value": 100},
            {"path": "/price", "type": "f", "value": 9.99},
            {"path": "/soldout", "type": "b", "value": False},
            {"path": "/details/page_count", "type": "i", "value": 345},
            {"path": "/details/author", "type": "s", "value": "Herman Melville"},
        ]

    def test_schema_list_with_restrictions(self):
        pars = Params()
        pars.int("count", min=3, max=10).set(1)
        pars.float("price", min=0.0, max=1.0).set(9.99)

        assert schema.schema_list(pars) == [
            {"path": "/count", "type": "i", "value": 0, "opts": {"min": 3, "max": 10}},
            {
                "path": "/price",
                "type": "f",
                "value": 0.0,
                "opts": {"min": 0.0, "max": 1.0},
            },
        ]

    def test_get_values(self):
        pars = Params()
        pars.int("count").set(1)
        pars.float("price").set(9.99)

        vals = schema.get_values(pars)

        assert vals["count"] == 1
        assert vals["price"] == 9.99
        assert json.loads(json.dumps(vals))["count"] == 1
        assert json.loads(json.dumps(vals))["price"] == 9.99

        pars.get("count").set(100)
        assert schema.get_values(pars)["count"] == 100

    def test_set_values(self):
        pars = Params()
        pars.int("count").set(1)
        pars.float("price").set(9.99)

        subpars = Params()
        subpars.bool("flag").set(True)
        pars.group("subgroup", subpars)

        schema.set_values(pars, {"count": 5, "price": 0.5, "subgroup": {"flag": False}})
        assert pars.get("count").val() == 5
        assert pars.get("price").val() == 0.5
        assert not pars.get("subgroup").get("flag").val()
