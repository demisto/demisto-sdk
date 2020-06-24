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
        if not isinstance(list1, list) or not isinstance(list2, list):
            return False

        if not len(list1) == len(list2):
            return False

        for item in list1:
            if item not in list2:
                return False

        return True

    @staticmethod
    def is_sets_equal(set1: set, set2: set):
        if not isinstance(set1, set) or not isinstance(set2, set):
            return False

        if not len(set1) == len(set2):
            return False

        for item in set1:
            if item not in set2:
                return False

        return True
