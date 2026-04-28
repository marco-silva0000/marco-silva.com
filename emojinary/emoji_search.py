import emoji
from django.http import JsonResponse


def emoji_search(request):
    """Search emojis by name. Returns JSON list of {emoji, name}."""
    q = request.GET.get("q", "").strip().lower()
    if not q or len(q) < 2:
        return JsonResponse([], safe=False)

    results = []
    for name, em in emoji.EMOJI_DATA.items():
        en_name = em.get("en", "").lower().replace(":", "").replace("_", " ")
        if q in en_name:
            results.append({"emoji": name, "name": en_name})
            if len(results) >= 50:
                break

    return JsonResponse(results, safe=False)
