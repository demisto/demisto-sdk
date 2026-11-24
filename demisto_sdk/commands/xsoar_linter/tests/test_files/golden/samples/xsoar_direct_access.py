"""Sample: direct subscript access to args/params (W9019)."""


def main() -> None:
    args = demisto.args()
    params = demisto.params()
    a = demisto.args()["a"]
    b = demisto.params()["b"]
    c = args["c"]
    d = params["d"]
    e = PARAMS["e"]
    f = dargs["f"]
    g = integration_parameters["g"]
    h = args.get("h")
    i = demisto.args().get("i")
    j = other["j"]
    k = args["k"]["nested"]
    l = int(args["l"])
    m: str = args["m"]
    args["n"] = 1
    o, p = args["o"], args["p"]
    q = self.args["q"]
    r = other.args()["r"]
    s = t = args["s"]
    return args["u"]
