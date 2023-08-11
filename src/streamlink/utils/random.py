from random import choice


CHOICES_NUM = "0123456789"
CHOICES_ALPHA_LOWER = "abcdefghijklmnopqrstuvwxyz"
CHOICES_ALPHA_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CHOICES_ALPHA = f"{CHOICES_ALPHA_LOWER}{CHOICES_ALPHA_UPPER}"
CHOICES_ALPHA_NUM = f"{CHOICES_NUM}{CHOICES_ALPHA}"
CHOICES_HEX_LOWER = f"{CHOICES_NUM}{CHOICES_ALPHA_LOWER[:6]}"
CHOICES_HEX_UPPER = f"{CHOICES_NUM}{CHOICES_ALPHA_UPPER[:6]}"


def random_token(length: int = 32, choices: str = CHOICES_ALPHA_NUM) -> str:
    return "".join(choice(choices) for _ in range(length))
