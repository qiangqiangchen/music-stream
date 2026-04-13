"""API router setup."""
from fastapi import APIRouter
from app.api.v1 import auth, tracks, media, lyrics, analytics, library, albums, artists, \
    system, admin, playlists, favorites, recent

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tracks.router, prefix="/tracks", tags=["Tracks"])
api_router.include_router(albums.router, prefix="/albums", tags=["Albums"])
api_router.include_router(artists.router, prefix="/artists", tags=["Artists"])
api_router.include_router(media.router, prefix="/media", tags=["Media"])
api_router.include_router(lyrics.router, prefix="/lyrics", tags=["Lyrics"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(library.router, prefix="/library", tags=["Library"])
api_router.include_router(system.router, prefix="/system", tags=["System"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(playlists.router, prefix="/playlists", tags=["Playlists"])
api_router.include_router(favorites.router, prefix="/favorites", tags=["Favorites"])
api_router.include_router(recent.router, prefix="/recent", tags=["Recent"])