from dataclasses import dataclass


@dataclass
class BaseCallbackData: ...


@dataclass
class SearchGotoShow(BaseCallbackData):
    search_id: str
    index: int


@dataclass
class SearchSelectShow(BaseCallbackData):
    search_id: str
    index: str


@dataclass
class SearchShowNotSelected(BaseCallbackData):
    search_id: str


@dataclass
class SearchSelectSeriesSeason(BaseCallbackData):
    search_id: str
    season: int


@dataclass
class SearchGotoRelease(BaseCallbackData):
    search_id: str
    index: str


@dataclass
class SearchSelectRelease(BaseCallbackData):
    search_id: str
    index: str
