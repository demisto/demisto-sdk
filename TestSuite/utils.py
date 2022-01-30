class IsEqualFunctions:
    @staticmethod
    def is_dicts_equal(dict1: dict, dict2: dict, lists_as_sets: bool = False):
        """
        :param dict1: first value to compare
        :param dict2: second value to compare
        :param lists_as_sets: used when comparing lists that originate from sets, where order does not matter.
        :return: whether the dictionaries are equal
        """

        if dict1.keys() != dict2.keys():
            return False

        for k, v in dict1.items():
            if isinstance(v, dict):
                return IsEqualFunctions.is_dicts_equal(v, dict2[k], lists_as_sets)

            if isinstance(v, list):
                if lists_as_sets:
                    return set(v) == set(dict2[k])
                else:
                    return v == dict2[k]

            if isinstance(v, set):
                return set(v) == set(dict2[k])

            return v == dict2[k]
