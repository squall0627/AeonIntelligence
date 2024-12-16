import re


def normalize_to_env_variable_name(name: str) -> str:
    # 文字、数字、またはアンダースコア以外の文字をすべてアンダースコアに置き換えます。
    env_variable_name = re.sub(r"[^A-Za-z0-9_]", "_", name).upper()

    # 正規化された名前が数字で始まるかどうかを確認します。
    if env_variable_name[0].isdigit():
        raise ValueError(
            f"Invalid environment variable name '{env_variable_name}': Cannot start with a digit."
        )

    return env_variable_name
