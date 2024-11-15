import yaml

from pathlib import Path
from typing import Self
from pydantic import BaseModel, ConfigDict


class AIBaseConfig(BaseModel):
    """
    Aeon Intelligence の基本設定クラス。

    このクラスは Pydantic の BaseModel を拡張し、ai-core の設定管理の基礎を提供します。

    属性:
        model_config (ConfigDict): Pydantic モデルの設定。余分な属性を禁止するように設定されており、定義されたスキーマに厳密に従います。

    クラスメソッド:
        from_yaml: YAML ファイルからクラスのインスタンスを作成します。
    """

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_yaml(cls, file_path: str | Path) -> Self:
        """
        YAML ファイルからクラスのインスタンスを作成します。

        引数:
        - file_path (str | Path): YAML ファイルへのパス。

        戻り値:
        - AIBaseConfig: YAML ファイルのデータで初期化されたクラスのインスタンス。
        """
        with open(file_path, "r") as stream:
            config_data = yaml.safe_load(stream)

        return cls(**config_data)