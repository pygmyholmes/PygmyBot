import discord
import asyncio
import yt_dlp

# Suppress noise about console usage from errors
yt_dlp.utils.bug_reports_message = lambda: ''

class YTDLPSource(discord.PCMVolumeTransformer):

    YTDLP_FORMAT_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
    }

    FFMPEG_OPTIONS = {
    'options': '-vn',
    }

    ytdlp = yt_dlp.YoutubeDL(YTDLP_FORMAT_OPTIONS)

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
    
    @classmethod
    async def extract_url_data(cls, url, event_loop=None, download=False):
        event_loop = event_loop or asyncio.get_event_loop()
        data = await event_loop.run_in_executor(None, lambda: YTDLPSource.ytdlp.extract_info(url, download))
        return data
    
    @classmethod
    def get_player_from_data(cls, data, stream):
        filename = data['url'] if stream else YTDLPSource.ytdlp.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **YTDLPSource.FFMPEG_OPTIONS), data=data)

    @classmethod
    async def play_from_url(cls, url, *, loop=None, stream=False):
        """Simply obtain the player for one song from a link."""
        data = await YTDLPSource.extract_url_data(url, event_loop=loop, download=not stream)

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        
        return YTDLPSource.get_player_from_data(data, stream)
