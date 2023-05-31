from enum import Enum
from typing import Union


# If you want to use specific java version, change these:
class Java8Flag:
    java_version = 'java8-jdk'


class Java17Flag:
    java_version = 'java17-jdk'


class Version:
    def __init__(self, name: str, flag):
        self.name: str = name
        self.flag = flag

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class Versions(Enum):
    V1_19_4 = Version("1.19.4", Java17Flag)
    V1_19_3 = Version("1.19.3", Java17Flag)
    V1_19_2 = Version("1.19.2", Java17Flag)
    V1_18_2 = Version("1.18.2", Java17Flag)
    V1_17_1 = Version("1.17.1", Java17Flag)
    V1_16_5 = Version("1.16.5", Java8Flag)
    V1_16_4 = Version("1.16.4", Java8Flag)
    V1_15_2 = Version("1.15.2", Java8Flag)
    V1_14_4 = Version("1.14.4", Java8Flag)
    V1_13_2 = Version("1.13.2", Java8Flag)
    V1_12_2 = Version("1.12.2", Java8Flag)
    V1_11_2 = Version("1.11.2", Java8Flag)
    V1_10_2 = Version("1.10.2", Java8Flag)
    V1_9_4 = Version("1.9.4", Java8Flag)
    V1_8_9 = Version("1.8.9", Java8Flag)
    V1_7_10 = Version("1.7.10", Java8Flag)

    @classmethod
    def get_by_version(cls, version: str) -> Union['Versions', None]:
        for x in cls:
            if x.value.name == version:
                return x
            else:
                continue

        return None
