import datetime
from pydantic import BaseModel, Field


CURRENT_YEAR = datetime.datetime.today().year


class StorageInModel(BaseModel):
    location: str = Field(max_length=200)
    description: str = Field(max_length=2000)


class StorageOutModel(StorageInModel):
    id: int | None = Field(ge=0, default=None)
    owner_id: int = Field(ge=0)


class GeographicInfoModel(BaseModel):
    country: str = Field(description="Country of origin.")
    region: str | None = Field(description="Origin region.", default='None')
    additional_info: str | None = Field(description="Extra information e.g., producer, specific vineyard(s).",
                                        default='None')


class WinesModel(BaseModel):
    name: str = Field(max_length=200)
    vintage: int = Field(gt=0, lt=3000, default=CURRENT_YEAR)
    grapes: str | None = Field(description="Provide a comma ',' separated list of all grapes in the wine. This is not "
                                           "enforced in any way, but suggested as an intuitively readable format. "
                                           "Add as many details as you wish e.g., the percentage per grape for blends. "
                                           "Note that t his field can be left empty for beers.",
                               default="None")
    type: str = Field(max_length=20,
                      description=("Wine examples: red, rose, white, fortified.\n"
                                   "Beer examples: stout, (BA) barley wine, Imp.Russian stout"))
    drink_from: datetime.date = Field(description="The year from which you would suggest drinking the wine.",
                                      default_factory=lambda x: datetime.datetime.strptime(
                                          str(x.vintage).rjust(5, '0'), '%Y').date())
    drink_before: datetime.date = Field(description="The last year in which you would suggest drinking the wine.")
    alcohol_vol_perc: float = Field(gt=0, lt=100, default=13.5)
    geographic_info: GeographicInfoModel = Field(description="Any information on the geographic origins of the bottle.")
    quality_signature: str | None = Field(max_length=200,
                                          description=("The wine appellation. Can be left empty for "
                                                       "beers or wines without an appellation."),
                                          default="None")


class CellarMinimalModel(BaseModel):
    storage_unit: int = Field(ge=0)
    bottle_size_cl: float = Field(gt=0, default=75)
    quantity: int = Field(gt=0)


class CellarOutModel(BaseModel):
    cellar_id: int = Field(ge=0)
    name: str = Field(max_length=200)
    vintage: int = Field(gt=0, lt=3000, default=CURRENT_YEAR)
    storage_unit: int = Field(ge=0)
    bottle_size_cl: float = Field(gt=0, default=75)
    quantity: int = Field(gt=0)
    wine_id: int = Field(ge=0)
    owner_id: int = Field(ge=0)
    drink_from: datetime.date = Field(description="The year from which you would suggest drinking the wine.",
                                      default_factory=lambda x: datetime.datetime.strptime(
                                          str(x.vintage).rjust(5, '0'), '%Y').date())
    drink_before: datetime.date = Field(description="The last year in which you would suggest drinking the wine.")


class CellarInModel(CellarMinimalModel):
    wine_info: WinesModel


class ConsumedBottleModel(BaseModel):
    wine_id: int = Field(ge=0)
    storage_unit: int = Field(ge=0)
    bottle_size_cl: float = Field(gt=0, default=75)
    quantity: int = Field(gt=0)


class RatingModel(BaseModel):
    rating: int = Field(gt=0, le=100, description="Rating on the Robert Parker scale", default=1)
    drinking_date: datetime.date | str = Field(description="When did you drink the rated beverage?")
    comments: str | None = Field(max_length=2000, default="None",
                                 description="Any additional comments such as tasting notes can be placed here.")


class RatingInDbModel(RatingModel):
    id: int = Field(ge=0)
    rater_id: int = Field(ge=0)
    wine_id: int = Field(ge=0)
