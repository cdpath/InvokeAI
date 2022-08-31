"""
Two helper classes for dealing with PNG images and their path names.
PngWriter -- Converts Images generated by T2I into PNGs, finds
             appropriate names for them, and writes prompt metadata
             into the PNG. Intended to be subclassable in order to
             create more complex naming schemes, including using the
             prompt for file/directory names.
PromptFormatter -- Utility for converting a Namespace of prompt parameters
             back into a formatted prompt string with command-line switches.
"""
import os
import re
from math import sqrt, floor, ceil
from PIL import Image, PngImagePlugin

# -------------------image generation utils-----


class PngWriter:
    def __init__(self, outdir, prompt=None, batch_size=1):
        self.outdir = outdir
        self.batch_size = batch_size
        self.prompt = prompt
        self.filepath = None
        self.files_written = []
        os.makedirs(outdir, exist_ok=True)

    def write_image(self, image, seed, upscaled=False):
        self.filepath = self.unique_filename(
            seed, upscaled, self.filepath
        )   # will increment name in some sensible way
        try:
            prompt = f'{self.prompt} -S{seed}'
            self.save_image_and_prompt_to_png(image, prompt, self.filepath)
        except IOError as e:
            print(e)
        if not upscaled:
            self.files_written.append([self.filepath, seed])

    def unique_filename(self, seed, upscaled=False, previouspath=None):
        revision = 1

        if previouspath is None:
            # sort reverse alphabetically until we find max+1
            dirlist = sorted(os.listdir(self.outdir), reverse=True)
            # find the first filename that matches our pattern or return 000000.0.png
            filename = next(
                (f for f in dirlist if re.match('^(\d+)\..*\.png', f)),
                '0000000.0.png',
            )
            basecount = int(filename.split('.', 1)[0])
            basecount += 1
            if self.batch_size > 1:
                filename = f'{basecount:06}.{seed}.01.png'
            else:
                filename = f'{basecount:06}.{seed}.png'
            return os.path.join(self.outdir, filename)

        else:
            basename = os.path.basename(previouspath)
            x = re.match('^(\d+)\..*\.png', basename)
            if not x:
                return self.unique_filename(seed, upscaled, previouspath)

            basecount = int(x.groups()[0])
            series = 0
            finished = False
            while not finished:
                series += 1
                filename = f'{basecount:06}.{seed}.png'
                path = os.path.join(self.outdir, filename)
                if self.batch_size > 1 or os.path.exists(path):
                    if upscaled:
                        break
                    filename = f'{basecount:06}.{seed}.{series:02}.png'
                path = os.path.join(self.outdir, filename)
                finished = not os.path.exists(path)
            return os.path.join(self.outdir, filename)

    def save_image_and_prompt_to_png(self, image, prompt, path):
        info = PngImagePlugin.PngInfo()
        info.add_text('Dream', prompt)
        image.save(path, 'PNG', pnginfo=info)

    def make_grid(self, image_list, rows=None, cols=None):
        image_cnt = len(image_list)
        if None in (rows, cols):
            rows = floor(sqrt(image_cnt))  # try to make it square
            cols = ceil(image_cnt / rows)
        width  = image_list[0].width
        height = image_list[0].height

        grid_img = Image.new('RGB', (width * cols, height * rows))
        i = 0
        for r in range(0, rows):
            for c in range(0, cols):
                if i>=len(image_list):
                    break
                grid_img.paste(image_list[i], (c * width, r * height))
                i = i + 1

        return grid_img


class PromptFormatter:
    def __init__(self, t2i, opt):
        self.t2i = t2i
        self.opt = opt

    # note: the t2i object should provide all these values.
    # there should be no need to or against opt values
    def normalize_prompt(self):
        """Normalize the prompt and switches"""
        t2i = self.t2i
        opt = self.opt

        switches = list()
        switches.append(f'"{opt.prompt}"')
        switches.append(f'-s{opt.steps        or t2i.steps}')
        switches.append(f'-W{opt.width        or t2i.width}')
        switches.append(f'-H{opt.height       or t2i.height}')
        switches.append(f'-C{opt.cfg_scale    or t2i.cfg_scale}')
        switches.append(f'-A{opt.sampler_name or t2i.sampler_name}')
        if opt.init_img:
            switches.append(f'-I{opt.init_img}')
        if opt.strength and opt.init_img is not None:
            switches.append(f'-f{opt.strength or t2i.strength}')
        if opt.gfpgan_strength:
            switches.append(f'-G{opt.gfpgan_strength}')
        if opt.upscale:
            switches.append(f'-U {" ".join([str(u) for u in opt.upscale])}')
        if t2i.full_precision:
            switches.append('-F')
        return ' '.join(switches)
