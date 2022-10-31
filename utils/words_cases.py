def get_word_in_case(number: int,
                     first_case: str,
                     second_case: str,
                     third_case: str) -> str:
    age_remains_second_case = (2, 3, 4)
    age_remains_third_case = (12, 13, 14)

    if number % 10 == 1 and number % 100 != 11:
        return first_case
    if (number % 10 in age_remains_second_case
            and number % 100 not in age_remains_third_case):
        return second_case
    return third_case
