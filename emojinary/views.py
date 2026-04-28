from django.shortcuts import get_object_or_404, redirect, render

from gamerooms.models import Room


def emojinary_index(request):
    return redirect("gamerooms:room-list")


def game(request, code, name):
    room = get_object_or_404(Room, code=code, is_active=True)
    return render(request, "emojinary/game.html", {"room": room, "player_name": name})
