from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

from moviepy.editor import CompositeVideoClip
from moviepy.editor import TextClip
from moviepy.editor import VideoFileClip
from moviepy.editor import concatenate_videoclips

from bot.constants import MAX_CLIPS
from bot.constants import READING_SPEED


@dataclass
class Segment:
    file: Path
    caption: str | None = None


@dataclass
class VideoData:
    is_new_video: bool = False
    segments: list[Segment] = field(default_factory=list)
    message_id_map: dict[int, int] = field(default_factory=dict)

    def add_segment(self, message_id: int, file: Path, caption: str | None = None):
        if len(self.segments) >= MAX_CLIPS:
            raise ValueError(f"Cannot add more than {MAX_CLIPS} clips")
        self.segments.append(Segment(file, caption))
        self.message_id_map[message_id] = len(self.segments) - 1

    def remove_segment(self, message_id: int):
        index = self.message_id_map.pop(message_id)
        self.segments.pop(index)

    def edit_caption(self, message_id: int, caption: str | None):
        index = self.message_id_map.get(message_id)
        if index is None:
            raise ValueError(f"Message ID {message_id} not found")
        self.segments[index].caption = caption

    async def render(self, output: Path) -> None:
        clips = []
        for segment in self.segments:
            clip = VideoFileClip(str(segment.file))
            if segment.caption is not None:
                txt_len = len(segment.caption.replace(" ", ""))
                video_width, _ = clip.size
                duration = max(txt_len / READING_SPEED, clip.duration)
                txt_clip = (
                    TextClip(
                        segment.caption,
                        fontsize=16,
                        size=(video_width, None),
                        align="North",
                        method="caption",
                        color="white",
                    )
                    .set_duration(duration)
                    .set_position(("center", "bottom"))
                )
                clip = clip.loop(duration=duration)  # type: ignore
                result = CompositeVideoClip([clip, txt_clip])
            else:
                result = clip
            clips.append(result)

        if len(clips) == 1:
            final = clips[0]
        else:
            final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(str(output))

    async def cleanup(self) -> None:
        for segment in self.segments:
            segment.file.unlink(True)
        self.segments.clear()
