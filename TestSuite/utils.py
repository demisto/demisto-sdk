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

        for k, v1 in dict1.items():
            v2 = dict2[k]

            if isinstance(v1, dict):
                comparison = IsEqualFunctions.is_dicts_equal(v1, v2, lists_as_sets)
            elif isinstance(v1, list):
                if lists_as_sets:
                    comparison = set(v1) == set(v2)
                else:
                    comparison = v1 == v2
            elif isinstance(v1, set):
                comparison = set(v1) == set(v2)
            else:
                comparison = v1 == v2

            if not comparison:
                return False

        return True
