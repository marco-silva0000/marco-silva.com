from datetime import datetime

from .version import get_version_info


def year(request):
    return {"year": datetime.now().year}


def version(request):
    info = get_version_info()
    return {
        "app_version": info["display"],
        "commit_hash": info["commit"],
        "version_counter": info["version"],
    }
