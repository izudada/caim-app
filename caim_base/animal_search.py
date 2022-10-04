from datetime import timedelta, datetime
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.core.exceptions import BadRequest
from .models import Animal, ZipCode, AnimalShortList, AnimalType, Awg


def query_animals(
    user,
    animal_type=AnimalType.DOG,
    zip=None,
    radius=None,
    age=None,
    sex=None,
    breed=None,
    awg_id=None,
    euth_date_within_days=None,
    goodwith_cats=None,
    goodwith_dogs=None,
    goodwith_kids=None,
    shortlist=False,
    sort="-created_at",
    hide_unpublished_animals=True,
    hide_unpublished_awgs=True,
):
    query = Animal.objects.filter(animal_type=animal_type).prefetch_related(
        "primary_breed", "secondary_breed", "awg"
    )

    if hide_unpublished_animals:
        query = query.filter(is_published=True)

    if hide_unpublished_awgs:
        query = query.filter(awg__status=Awg.AwgStatus.PUBLISHED)

    zip_info = None
    if zip:
        zip_info = ZipCode.objects.filter(zip_code=zip).first()
        if not zip_info:
            raise BadRequest("Invalid ZIP parameter")
        query = query.annotate(
            distance=Distance("awg__geo_location", zip_info.geo_location)
        )

    if age:
        query = query.filter(age=age.upper())

    if awg_id:
        query = query.filter(awg_id=awg_id)

    if euth_date_within_days:
        td = timedelta(days=euth_date_within_days)
        # @todo timezone (UTC by default)
        future_date = (datetime.now() + td).replace(hour=23, minute=59, second=59)
        query = query.filter(euth_date__lte=future_date)

    if sex:
        query = query.filter(sex=sex.upper())

    if breed:
        query = query.filter(
            Q(primary_breed__slug=breed) | Q(secondary_breed__slug=breed)
        )

    if goodwith_cats:
        query = query.filter(behaviour_cats=Animal.AnimalBehaviourGrade.GOOD)

    if goodwith_dogs:
        query = query.filter(behaviour_dogs=Animal.AnimalBehaviourGrade.GOOD)

    if goodwith_kids:
        query = query.filter(behaviour_kids=Animal.AnimalBehaviourGrade.GOOD)

    if radius and zip:
        radius_meters = radius * 1609.34  # Miles to meters
        query = query.filter(distance__lte=radius_meters)

    if sort:
        query = query.order_by(sort, "id")

    if shortlist and user.is_authenticated:
        shortlists = AnimalShortList.objects.filter(user=user.id)
        shortlist_animal_ids = [s.animal_id for s in shortlists]
        query = query.filter(id__in=shortlist_animal_ids)

    return query
