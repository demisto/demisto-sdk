class IsEqualFunctions:
    @staticmethod
    def is_dicts_equal(dict1: dict, dict2: dict, simple_comparison: bool):
        dict1 = dict(dict1)
        dict2 = dict(dict2)

        if simple_comparison:
            return dict1 == dict2

        if dict1.keys() != dict2.keys():
            return False

        for k, v in dict1.items():
            if isinstance(v, dict):
                return IsEqualFunctions.is_dicts_equal(v, dict2[k], simple_comparison)
            if isinstance(v, list):
                return IsEqualFunctions.is_lists_equal(v, dict2[k])
            if isinstance(v, set):
                return IsEqualFunctions.is_sets_equal(v, dict2[k])
            return v == dict2[k]

    @staticmethod
    def is_lists_equal(list1: list, list2: list):
        return list(list1) == list(list2)

    @staticmethod
    def is_sets_equal(set1: set, set2: set):
        return set(set1) == set(set2)
