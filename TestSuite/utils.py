from collections import Counter


class IsEqualFunctions:
    @staticmethod
    def is_dicts_equal(dict1: dict, dict2: dict):
        if not isinstance(dict1, dict) or not isinstance(dict2, dict):
            return False

        if sorted(list(dict1.keys())) != sorted(list(dict2.keys())):
            return False

        for key, dict1_value in dict1.items():
            dict2_value = dict2.get(key)

            if not isinstance(dict2_value, type(dict1_value)):
                return False

            if isinstance(dict1_value, dict):
                if not IsEqualFunctions.is_dicts_equal(dict1_value, dict2_value):
                    return False

            if isinstance(dict1_value, list):
                IsEqualFunctions.is_lists_equal(dict1_value, dict2_value)

            else:
                if dict1_value != dict2_value:
                    return False

        return True

    @staticmethod
    def is_lists_equal(list1: list, list2: list):
        return isinstance(list1, list) \
            and isinstance(list2, list) \
            and Counter(list1) == Counter(list2)  # regardless of order

    @staticmethod
    def is_sets_equal(set1: set, set2: set):
        return isinstance(set1, set) \
            and isinstance(set2, set) \
            and set1 == set2
