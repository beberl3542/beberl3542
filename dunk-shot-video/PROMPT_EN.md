# Prompt (English, for actual generation)

## Main prompt

```
Photorealistic 4-second live-action style video, indoor high school gymnasium basketball court.
Polished hardwood floor with painted court lines, high ceiling with exposed steel trusses and bright overhead gym lights, padded wall and empty bleachers in the background behind the basket.

Camera: fixed tripod inside the court, placed on the center axis directly in line with the basket, about 7-8 meters back from the hoop, lens height 100 cm, perfectly level, no tilt, no pan, no zoom, no handheld shake. Standard 1x lens (approx. 26mm full-frame equivalent), natural undistorted perspective. The rim and backboard sit in the upper center of the frame, fully visible.

Subject: one athletic male basketball player, 180 cm tall, seen from behind. He enters from the lower right of the frame, dribbles two or three steps toward the basket with his back to the camera, takes a two-step gather, jumps and throws down a powerful one-handed right-hand dunk. He grabs the rim for a split second, lets go and lands on both feet. The ball drops through the net and bounces on the floor. The rim and net shake from the impact.

Wardrobe: plain sleeveless basketball jersey and shorts with no logos or text, high-top basketball sneakers, athletic socks.

Look: natural slightly cool gym lighting, realistic floor reflections and a soft shadow under the player, subtle realistic motion blur, smooth 60fps-like motion, neutral color grade, sharp focus on the player and the rim. Real footage look, not CGI.
```

## Negative prompt (for models that support it)

```
camera movement, pan, zoom, handheld shake, slow motion, multiple players, crowd, spectators, text, captions, logos, watermark, subtitles, distorted limbs, extra limbs, malformed hands, extra fingers, duplicated ball, warped rim, bent backboard, anime, illustration, cartoon, CGI look, blurry, low resolution, flicker, jitter
```

## Short variant (for models with tight prompt length limits)

```
Static tripod shot, 100 cm high, level, 1x standard lens, inside an indoor gymnasium basketball court, camera directly behind and in line with the basket about 7 m back. A 180 cm tall male player in plain jersey and high-top basketball shoes runs away from the camera toward the hoop, jumps and slams a one-handed dunk, hangs on the rim briefly, lands. Photorealistic, natural gym lighting, no camera motion, 4 seconds.
```

## Recommended settings

| Setting | Value |
|---|---|
| Aspect ratio | 16:9 |
| Duration | 4 s (or 5 s, trim to 4 s afterwards) |
| Resolution | Highest available (1080p or above) |
| Frame rate | Highest available (24/30 fps native, interpolate to 60 fps in post) |
| Motion strength | Medium-high |
| Camera control (if the model has it) | Static / locked |
| Seed | Fix a seed and compare 4-6 variations |

## Model-specific notes

- **Veo (Google)**: paste the main prompt as-is. Veo respects "no camera movement" well. Choose 1080p, 16:9.
- **Sora (OpenAI)**: paste the main prompt. If the camera drifts, add "locked-off tripod shot" at the very beginning of the prompt.
- **Kling**: use the main prompt plus the negative prompt. Set camera control to "static". Use "Professional" mode for higher quality.
- **Runway Gen-4**: use the short variant, and set Camera Control to no motion. Optionally first generate a still reference frame of the empty gym from the same camera position and use image-to-video.
- **Hailuo / MiniMax**: main prompt plus negative prompt. Enable "camera fixed" if available.

## Tips for consistent results

- If the player's height reads wrong, add: "the rim is at regulation 305 cm; the player's reach at full extension just clears the rim".
- If the model puts the camera behind the backboard instead of behind the player, add: "the backboard faces the camera, we see the front of the rim and the net, the player runs away from the camera".
- If you need the player facing the camera instead, replace "seen from behind" with "seen from the front, running toward the camera" and move the camera under the basket. This is a different shot from the one specified here.
