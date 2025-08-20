from django.db.models import Max

from bookmarks.models import BookmarkBundle, User


def create_bundle(bundle: BookmarkBundle, current_user: User):
    bundle.owner = current_user
    if bundle.order is None:
        max_order_result = BookmarkBundle.objects.filter(owner=current_user).aggregate(
            Max("order", default=-1)
        )
        bundle.order = max_order_result["order__max"] + 1
    bundle.save()
    return bundle


def move_bundle(bundle_to_move: BookmarkBundle, new_order: int):
    user_bundles = list(
        BookmarkBundle.objects.filter(owner=bundle_to_move.owner).order_by("order")
    )

    if new_order != user_bundles.index(bundle_to_move):
        user_bundles.remove(bundle_to_move)
        user_bundles.insert(new_order, bundle_to_move)
        for bundle_index, bundle in enumerate(user_bundles):
            bundle.order = bundle_index

        BookmarkBundle.objects.bulk_update(user_bundles, ["order"])


def delete_bundle(bundle: BookmarkBundle):
    bundle.delete()

    user_bundles = BookmarkBundle.objects.filter(owner=bundle.owner).order_by("order")
    for index, user_bundle in enumerate(user_bundles):
        user_bundle.order = index
    BookmarkBundle.objects.bulk_update(user_bundles, ["order"])
