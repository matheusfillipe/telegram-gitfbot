from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

from moviepy.editor import CompositeVideoClip
from moviepy.editor import TextClip
from moviepy.editor import VideoFileClip
from moviepy.editor import concatenate_videoclips


@dataclass
class Segment:
    file: Path
    caption: str | None = None


@dataclass
class VideoData:
    is_new_video: bool = False
    name: str = ""
    segments: list[Segment] = field(default_factory=list)

    def add_segment(self, file: Path, caption: str | None = None):
        self.segments.append(Segment(file, caption))

    async def render(self, output: Path) -> None:
        clips = []
        for segment in self.segments:
            clip = VideoFileClip(str(segment.file))
            if segment.caption is not None:
                txt_clip = TextClip(segment.caption, fontsize=70, align="South", method="caption")
                result = CompositeVideoClip([clip, txt_clip])
            else:
                result = clip
            clips.append(result)
        final = concatenate_videoclips(clips)
        final.write_videofile(str(output))

    async def cleanup(self) -> None:
        for segment in self.segments:
            segment.file.unlink()
