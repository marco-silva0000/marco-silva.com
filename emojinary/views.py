from django.shortcuts import get_object_or_404, render

from gamerooms.models import Room


def game(request, code, name):
    room = get_object_or_404(Room, code=code, is_active=True)
    return render(request, "emojinary/game.html", {"room": room, "player_name": name})
