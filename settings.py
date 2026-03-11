import os

BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
OWNER_ID     = int(os.environ.get("OWNER_ID", "0"))
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
SHODAN_KEY   = os.environ.get("SHODAN_KEY", "")
HUNTER_KEY   = os.environ.get("HUNTER_KEY", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,*/*",
}
TIMEOUT = 12

USERNAME_PLATFORMS = [
    {"name":"Instagram",   "url":"https://instagram.com/{}"},
    {"name":"Twitter/X",   "url":"https://twitter.com/{}"},
    {"name":"TikTok",      "url":"https://tiktok.com/@{}"},
    {"name":"Facebook",    "url":"https://facebook.com/{}"},
    {"name":"YouTube",     "url":"https://youtube.com/@{}"},
    {"name":"Pinterest",   "url":"https://pinterest.com/{}"},
    {"name":"Twitch",      "url":"https://twitch.tv/{}"},
    {"name":"Reddit",      "url":"https://reddit.com/user/{}"},
    {"name":"Tumblr",      "url":"https://{}.tumblr.com"},
    {"name":"GitHub",      "url":"https://github.com/{}"},
    {"name":"GitLab",      "url":"https://gitlab.com/{}"},
    {"name":"Bitbucket",   "url":"https://bitbucket.org/{}"},
    {"name":"NPM",         "url":"https://npmjs.com/~{}"},
    {"name":"PyPI",        "url":"https://pypi.org/user/{}"},
    {"name":"StackOverflow","url":"https://stackoverflow.com/users/{}"},
    {"name":"HackerNews",  "url":"https://news.ycombinator.com/user?id={}"},
    {"name":"Replit",      "url":"https://replit.com/@{}"},
    {"name":"Codepen",     "url":"https://codepen.io/{}"},
    {"name":"Dev.to",      "url":"https://dev.to/{}"},
    {"name":"Medium",      "url":"https://medium.com/@{}"},
    {"name":"LinkedIn",    "url":"https://linkedin.com/in/{}"},
    {"name":"Linktree",    "url":"https://linktr.ee/{}"},
    {"name":"Behance",     "url":"https://behance.net/{}"},
    {"name":"Dribbble",    "url":"https://dribbble.com/{}"},
    {"name":"SoundCloud",  "url":"https://soundcloud.com/{}"},
    {"name":"Spotify",     "url":"https://open.spotify.com/user/{}"},
    {"name":"Vimeo",       "url":"https://vimeo.com/{}"},
    {"name":"Keybase",     "url":"https://keybase.io/{}"},
    {"name":"Telegram",    "url":"https://t.me/{}"},
    {"name":"Steam",       "url":"https://steamcommunity.com/id/{}"},
    {"name":"Patreon",     "url":"https://patreon.com/{}"},
    {"name":"Substack",    "url":"https://{}.substack.com"},
    {"name":"AboutMe",     "url":"https://about.me/{}"},
    {"name":"HackerOne",   "url":"https://hackerone.com/{}"},
    {"name":"BugCrowd",    "url":"https://bugcrowd.com/{}"},
    {"name":"DockerHub",   "url":"https://hub.docker.com/u/{}"},
    {"name":"ProductHunt", "url":"https://producthunt.com/@{}"},
    {"name":"Mastodon",    "url":"https://mastodon.social/@{}"},
    {"name":"Snapchat",    "url":"https://snapchat.com/add/{}"},
    {"name":"DeviantArt",  "url":"https://deviantart.com/{}"},
    {"name":"Flickr",      "url":"https://flickr.com/people/{}"},
    {"name":"Gravatar",    "url":"https://gravatar.com/{}"},
    {"name":"AngelList",   "url":"https://angel.co/u/{}"},
]
