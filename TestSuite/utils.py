class IsEqualFunctions:
    @staticmethod
    def is_dicts_equal(dict1: dict, dict2: dict):
        return dict(dict1) == dict(dict2)

    @staticmethod
    def is_lists_equal(list1: list, list2: list):
        return list(list1) == list(list2)

    @staticmethod
    def is_sets_equal(set1: set, set2: set):
        return set(set1) == set(set2)
