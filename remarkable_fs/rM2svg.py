# This code copied from https://github.com/phil777/maxio
# and licensed under the LGPL, version 3.

import sys
import struct
import os.path
import argparse
#import poppler
import cairocffi as cairo


__prog_name__ = "rM2svg"
__version__ = "0.0.1beta"


# Size
x_width = 1404
y_width = 1872

# Mappings
stroke_colour={
    0 : (0,0,0),
    1 : (128,128,128),
    2 : (255,255,255),
}
'''stroke_width={
    0x3ff00000 : 2,
    0x40000000 : 4,
    0x40080000 : 8,
}'''


def main():
    parser = argparse.ArgumentParser(prog=__prog_name__)
    parser.add_argument("-i",
                        "--input",
                        help=".lines input file",
                        required=True,
                        metavar="FILENAME",
                        #type=argparse.FileType('r')
                        )
    parser.add_argument("-p",
                        "--pdf",
                        help=".pdf input file",
                        required=False,
                        metavar="PDF")
    parser.add_argument("-o",
                        "--output",
                        help="prefix for output files",
                        required=True,
                        metavar="NAME",
                        #type=argparse.FileType('w')
                        )
    parser.add_argument('--version',
                        action='version',
                        version='%(prog)s {version}'.format(version=__version__))
    args = parser.parse_args()

    if not os.path.exists(args.input):
        parser.error('The file "{}" does not exist!'.format(args.input))

    lines2cairo(args.input, args.output, args.pdf)


def abort(msg):
    print(msg)
    sys.exit(1)


def lines2cairo(input_file, output_name, pdf_name):
    # Read the file in memory. Consider optimising by reading chunks.
    #with open(input_file, 'rb') as f:
    #    data = f.read()
    data = input_file.read()
    offset = 0

    # Is this a reMarkable .lines file?
    expected_header=b'reMarkable lines with selections and layers'
    if len(data) < len(expected_header) + 4:
        abort('File too short to be a valid file')

    fmt = '<{}sI'.format(len(expected_header))
    header, npages = struct.unpack_from(fmt, data, offset); offset += struct.calcsize(fmt)
    if header != expected_header or npages < 1:
        abort('Not a valid reMarkable file: <header={}><npages={}>'.format(header, npages))



    #pdfdoc = poppler.document_new_from_file("file://"+os.path.realpath(pdf_name),"") if pdf_name else None
    pdfdoc = None

    if pdfdoc:
        pdfpage = pdfdoc.get_page(0)
        pdfx,pdfy = pdfpage.get_size()
        print "page %.2f %.2f" % (pdfx,pdfy)
        xfactor = pdfx/x_width
        yfactor = pdfy/y_width
        xfactor = yfactor = max(xfactor, yfactor)
    else:
        xfactor = yfactor = 1
        pdfx = x_width
        pdfy = y_width


    surface = cairo.PDFSurface(output_name, pdfx, pdfy)



    # Iterate through pages (There is at least one)


    for page in range(npages):

        fmt = '<BBH' # TODO might be 'I'
        nlayers, b_unk, h_unk = struct.unpack_from(fmt, data, offset); offset += struct.calcsize(fmt)
        if b_unk != 0 or h_unk != 0: # Might indicate which layers are visible.
            print('Unexpected value on page {} after nlayers'.format(page + 1))



        context = cairo.Context(surface)


#            pdfpage.render_for_printing(context)


        # Iterate through layers on the page (There is at least one)
        for layer in range(nlayers):
            fmt = '<I'
            (nstrokes,) = struct.unpack_from(fmt, data, offset); offset += struct.calcsize(fmt)

            # Iterate through the strokes in the layer (If there is any)
            for stroke in range(nstrokes):
                fmt = '<IIIfI'
                pen, colour, i_unk, width, nsegments = struct.unpack_from(fmt, data, offset); offset += struct.calcsize(fmt)
                opacity = 1
                last_x = -1.; last_y = -1.
                #if i_unk != 0: # No theory on that one
                    #print('Unexpected value at offset {}'.format(offset - 12))
                if pen == 0 or pen == 1:
                    pass # Dynamic width, will be truncated into several strokes
                elif pen == 2 or pen == 4: # Pen / Fineliner
                    width = 32 * width * width - 116 * width + 107
                elif pen == 3: # Marker
                    width = 64 * width - 112
                    opacity = 0.9
                elif pen == 5: # Highlighter
                    width = 30
                    opacity = 0.2
                elif pen == 6: # Eraser
                    width = 1280 * width * width - 4800 * width + 4510
                    colour = 2
                elif pen == 7: # Pencil-Sharp
                    width = 16 * width - 27
                    opacity = 0.9
                elif pen == 8: # Erase area
                    opacity = 0.
                else: 
                    print('Unknown pen: {}'.format(pen))
                    opacity = 0.


                fmt = '<fffff'
                fmtsz = struct.calcsize(fmt)
                segments = []
                # Iterate through the segments to form a polyline
                for segment in range(nsegments):
                    segments.append(struct.unpack_from(fmt, data, offset))
                    offset += fmtsz

                context.new_path()
                for xpos, ypos, pressure, tilt, i_unk2 in segments:
                    if pen == 0:
                        width = (5. * tilt) * (6. * width - 10) * (1 + 2. * pressure * pressure * pressure)
                    elif pen == 1:
                        width = (10. * tilt -2) * (8. * width - 14)
                        opacity = (pressure - .2) * (pressure - .2)
                    context.set_source_rgba(*stroke_colour[colour], alpha=opacity)
                    context.set_line_width(width*xfactor)
                    context.line_to(xpos*xfactor, ypos*yfactor)
                context.stroke()

        context.show_page()

    surface.finish()

if __name__ == "__main__":
    main()
