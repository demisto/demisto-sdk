from collections import OrderedDict


def order_dict(data):
    """
    Order dict by default order
    """
    return OrderedDict({k: order_dict(v) if isinstance(v, dict) else v
                        for k, v in sorted(data.items())})
