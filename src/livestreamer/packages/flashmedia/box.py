from ctypes import BigEndianStructure, Union, c_uint8, c_uint16, c_uint32

from .compat import *
from .error import *
from .packet import *
from .util import *

class Box(Packet):
    def __init__(self, type, total_size, payload, extended_size=False):
        self.type = type
        self.total_size = total_size
        self.payload = payload
        self.extended_size = extended_size

    @property
    def size(self):
        size = 8
        size += self.payload.size

        if size > 0xFFFFFFFF or self.extended_size:
            size += 8

        return size

    @classmethod
    def _deserialize(cls, io):
        size = io.read_u32()
        type_ = io.read_padded(4)
        header_size = 8
        extended_size = False

        if size == 1:
            size = io.read_u64()
            header_size += 8
            extended_size = True

        if type_ in PayloadTypes:
            parent_data_left = io.data_left
            io.data_left = size - header_size

            payload = PayloadTypes[type_].deserialize(io=io)

            if parent_data_left is not None:
                io.data_left = parent_data_left - payload.size
            else:
                io.data_left = None
        else:
            if size == 0:
                data = io.read()
            else:
                data = io.read(size - header_size)

            payload = RawPayload(data)

        return cls(type_, size, payload, extended_size)

    def _serialize(self, packet):
        size = self.payload.size

        if size > 0xFFFFFFFF or self.extended_size:
            packet.write_u32(1)
        else:
            packet.write_u32(size + 8)

        packet.write_padded(self.type, 4)

        if size > 0xFFFFFFFF or self.extended_size:
            packet.write_u64(size + 16)

        if isinstance(self.payload, BoxPayload):
            self.payload.serialize(packet)
        else:
            packet.write(self.payload)

class BoxPayload(Packet):
    @property
    def size(self):
        return 0

    @classmethod
    def box(cls, *args, **kw):
        type_ = None

        for name, kls in PayloadTypes.items():
            if kls == cls:
                type_ = name
                break

        payload = cls(*args, **kw)

        return Box(type_, 0, payload)

class BoxContainer(BoxPayload):
    def __init__(self, boxes):
        self.boxes = boxes

    @property
    def size(self):
        size = 0
        for box in self.boxes:
            size += box.size

        return size

    def _serialize(self, packet):
        for box in self.boxes:
            box.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        boxes = []

        while io.data_left > 0:
            box = Box.deserialize(io=io)
            boxes.append(box)

        return cls(boxes)


class BoxContainerSingle(BoxPayload):
    def __init__(self, box):
        self.box = box

    @property
    def size(self):
        return self.box.size

    def _serialize(self, packet):
        self.box.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        box = Box.deserialize(io=io)

        return cls(box)




class RawPayload(BoxPayload):
    def __init__(self, data):
        self.data = data

    def __repr__(self):
        return "<RawPayload size={0}>".format(self.size)

    @property
    def size(self):
        return len(self.data)

    @classmethod
    def _deserialize(cls, io):
        data = io.read()

        return cls(data)

    def _serialize(self, packet):
        packet.write(self.data)

class BoxPayloadFTYP(BoxPayload):
    def __init__(self, major_brand="f4v", minor_version=0,
                 compatible_brands=["isom", "mp42", "m4v"]):
        self.major_brand = major_brand
        self.minor_version = minor_version
        self.compatible_brands = compatible_brands

    @property
    def size(self):
        return 4+4+(len(self.compatible_brands)*4)

    def _serialize(self, packet):
        packet.write_padded(self.major_brand, 4)
        packet.write_u32(self.minor_version)

        for brand in self.compatible_brands:
            packet.write_padded(brand, 4)

    @classmethod
    def _deserialize(cls, io):
        major_brand = io.read_padded(4)
        minor_version = io.read_u32()
        compatible_brands = []

        while io.data_left > 0:
            brand = io.read_padded(4)
            compatible_brands.append(brand)

        return cls(major_brand, minor_version,
                   compatible_brands)


class BoxPayloadMVHD(BoxPayload):
    def __init__(self, version=0, creation_time=0, modification_time=0,
                 time_scale=1000, duration=0, rate=1.0, volume=1.0,
                 matrix=[65536, 0, 0, 0, 65536, 0, 0, 0, 1073741824],
                 next_track_id=0):
        self.version = version
        self.creation_time = creation_time
        self.modification_time = modification_time
        self.time_scale = time_scale
        self.duration = duration
        self.rate = rate
        self.volume = volume
        self.matrix = matrix
        self.next_track_id = next_track_id

    @property
    def size(self):
        size = 1+3+4+4+2+2+4+4+(9*4)+(6*4)+4

        if self.version == 1:
            size += 3*8
        else:
            size += 3*4

        return size

    def _serialize(self, packet):
        packet.write_u8(self.version)
        packet.write_u24(0) # Reserved

        packet.write_u3264(self.version, self.creation_time)
        packet.write_u3264(self.version, self.modification_time)
        packet.write_u32(self.time_scale)
        packet.write_u3264(self.version, self.duration)

        packet.write_s16_16(self.rate)
        packet.write_s8_8(self.volume)

        packet.write_u16(0) # Reserved
        packet.write_u32(0) # Reserved
        packet.write_u32(0) # Reserved

        for m in self.matrix:
            packet.write_u32(m)

        for i in range(6):
            packet.write_u32(0) # Reserved

        packet.write_u32(self.next_track_id)

    @classmethod
    def _deserialize(cls, io):
        version = io.read_u8()
        io.read_u24() # Reserved

        creation_time = io.read_u3264(version)
        modification_time = io.read_u3264(version)
        time_scale = io.read_u32()
        duration = io.read_u3264(version)

        rate = io.read_s16_16()
        volume = io.read_s8_8()

        io.read_u16() # Reserved
        io.read_u32() # Reserved
        io.read_u32() # Reserved

        matrix = []
        for i in range(9):
            matrix.append(io.read_u32())

        for i in range(6):
            io.read_u32() # Reserved

        next_track_id = io.read_u32()

        return cls(version, creation_time,
                   modification_time, time_scale, duration,
                   rate, volume, matrix, next_track_id)


class SampleFlags(BoxPayload):
    class Flags(Union):
        class Bits(BigEndianStructure):
            _fields_ = [("reserved", c_uint8, 6),
                        ("sample_depends_on", c_uint8, 2),
                        ("sample_is_depended_on", c_uint8, 2),
                        ("sample_has_redundancy", c_uint8, 2),
                        ("sample_padding_value", c_uint8, 3),
                        ("sample_is_difference_sample", c_uint8, 1),
                        ("sample_degradation_priority", c_uint16, 16)]

        _fields_ = [("bit", Bits), ("byte", c_uint32)]

    def __init__(self, sample_depends_on, sample_is_depended_on,
                 sample_has_redundancy, sample_padding_value,
                 sample_is_difference_sample, sample_degradation_priority):

        self.flags = self.Flags()
        self.flags.bit.reserved = 0 # Reserved
        self.flags.bit.sample_depends_on = sample_depends_on
        self.flags.bit.sample_is_depended_on = sample_is_depended_on
        self.flags.bit.sample_has_redundancy = sample_has_redundancy
        self.flags.bit.sample_padding_value = sample_padding_value
        self.flags.bit.sample_is_difference_sample = sample_is_difference_sample
        self.flags.bit.sample_degradation_priority = sample_degradation_priority

    @property
    def size(self):
        return 4

    def _serialize(self, packet):
        packet.write_u32(self.flags.byte)

    @classmethod
    def _deserialize(cls, io):
        flags = cls.Flags()
        flags.byte = io.read_u32()

        return cls(flags.bit.sample_depends_on, flags.bit.sample_is_depended_on,
                   flags.bit.sample_has_redundancy, flags.bit.sample_padding_value,
                   flags.bit.sample_is_difference_sample, flags.bit.sample_degradation_priority)


class BoxPayloadTREX(BoxPayload):
    def __init__(self, version, track_id,
                 default_sample_description_index,
                 default_sample_duration, default_sample_size,
                 default_sample_flags):
        self.version = version
        self.track_id = track_id
        self.default_sample_description_index = default_sample_description_index
        self.default_sample_duration = default_sample_duration
        self.default_sample_size = default_sample_size
        self.default_sample_flags = default_sample_flags

    @property
    def size(self):
        return 1+3+4+4+4+4+self.default_sample_flags.size

    def _serialize(self, packet):
        packet.write_u8(self.version)
        packet.write_u24(0) # Reserved
        packet.write_u32(self.track_id)
        packet.write_u32(self.default_sample_description_index)
        packet.write_u32(self.default_sample_duration)
        packet.write_u32(self.default_sample_size)
        self.default_sample_flags.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        version = io.read_u8()
        flags = io.read_u24()
        track_id = io.read_u32()
        default_sample_description_index = io.read_u32()
        default_sample_duration = io.read_u32()
        default_sample_size = io.read_u32()
        default_sample_flags = SampleFlags.deserialize(io=io)

        return cls(version, track_id,
                   default_sample_description_index,
                   default_sample_duration, default_sample_size,
                   default_sample_flags)


class BoxPayloadTKHD(BoxPayload):
    def __init__(self, version=0, flags=1, creation_time=0, modification_time=0,
                 track_id=1, duration=0, layer=0, alternate_group=0, volume=0.0,
                 transform_matrix=[65536, 0, 0, 0, 65536, 0, 0, 0, 1073741824],
                 width=0.0, height=0.0):
        self.version = version
        self.flags = flags
        self.creation_time = creation_time
        self.modification_time = modification_time
        self.track_id = track_id
        self.duration = duration
        self.layer = layer
        self.alternate_group = alternate_group
        self.volume = volume
        self.transform_matrix = transform_matrix
        self.width = width
        self.height = height

    @property
    def size(self):
        size = 1+3+4+4+4+4+4+(4*2)+2+2+2+2+(9*4)+4+4

        if self.version == 1:
            size += 4*3

        return size

    def _serialize(self, packet):
        packet.write_u8(self.version)
        packet.write_u24(self.flags)

        packet.write_u3264(self.version, self.creation_time)
        packet.write_u3264(self.version, self.modification_time)
        packet.write_u32(self.track_id)
        packet.write_u32(0) # Reserved
        packet.write_u3264(self.version, self.duration)

        for i in range(2):
            packet.write_u32(0) # Reserved

        packet.write_s16(self.layer)
        packet.write_s16(self.alternate_group)
        packet.write_s8_8(self.volume)
        packet.write_u16(0) # Reserved

        for i in range(9):
            packet.write_u32(self.transform_matrix[i])

        packet.write_s16_16(self.width)
        packet.write_s16_16(self.height)

    @classmethod
    def _deserialize(cls, io):
        version = io.read_u8()
        flags = io.read_u24()

        creation_time = io.read_u3264(version)
        modification_time = io.read_u3264(version)
        track_id = io.read_u32()
        io.read_u32() # Reserved
        duration = io.read_u3264(version)

        for i in range(2):
            io.read_u32() # Reserved

        layer = io.read_s16()
        alternate_group = io.read_s16()
        volume = io.read_s8_8()
        io.read_u16() # Reserved

        transform_matrix = []
        for i in range(9):
            transform_matrix.append(io.read_s32())

        width = io.read_s16_16()
        height = io.read_s16_16()

        return cls(version, flags, creation_time, modification_time,
                   track_id, duration, layer, alternate_group, volume,
                   transform_matrix, width, height)


class BoxPayloadMDHD(BoxPayload):
    def __init__(self, version=0, creation_time=0, modification_time=0,
                 time_scale=1000, duration=0, language="eng"):
        self.version = version
        self.creation_time = creation_time
        self.modification_time = modification_time
        self.time_scale = time_scale
        self.duration = duration
        self.language = language

    @property
    def size(self):
        size = 1+3+4+4+4+4+2+2

        if self.version == 1:
            size += 4*3

        return size

    def _serialize(self, packet):
        packet.write_u8(self.version)
        packet.write_u24(0) # Reserved

        packet.write_u3264(self.version, self.creation_time)
        packet.write_u3264(self.version, self.modification_time)
        packet.write_u32(self.time_scale)
        packet.write_u3264(self.version, self.duration)

        packet.write_s16(iso639_to_lang(self.language))
        packet.write_u16(0) # Reserved

    @classmethod
    def _deserialize(cls, io):
        version = io.read_u8()
        io.read_u24() # Reserved

        creation_time = io.read_u3264(version)
        modification_time = io.read_u3264(version)
        time_scale = io.read_u32()
        duration = io.read_u3264(version)

        language = lang_to_iso639(io.read_u16())
        io.read_u16() # Reserved

        return cls(version, creation_time, modification_time,
                   time_scale, duration, language)


class BoxPayloadHDLR(BoxPayload):
    def __init__(self, version=0, predefined=0, handler_type="vide",
                 name=""):
        self.version = version
        self.predefined = predefined
        self.handler_type = handler_type
        self.name = name

    @property
    def size(self):
        size = 1+3+4+4+(3*4)
        size += len(self.name)

        return size

    def _serialize(self, packet):
        packet.write_u8(self.version)
        packet.write_u24(0) # Reserved
        packet.write_u32(self.predefined)
        packet.write_padded(self.handler_type, 4)

        for i in range(3):
            packet.write_u32(0) # Reserved

        packet.write(bytes(self.name, "utf8"))
        #packet.write_string(self.name)

    @classmethod
    def _deserialize(cls, io):
        version = io.read_u8()
        flags = io.read_u24() # Reserved

        predefined = io.read_u32()
        handler_type = io.read_padded(4)

        for i in range(3):
            io.read_u32() # Reserved

        name = io.read_string()

        return cls(version, predefined, handler_type,
                   name)


class BoxPayloadVMHD(BoxPayload):
    def __init__(self, version=0, flags=1, graphics_mode=0, op_color=[0, 0, 0]):
        self.version = version
        self.flags = flags
        self.graphics_mode = graphics_mode
        self.op_color = op_color

    @property
    def size(self):
        return 1+3+2+(3*2)

    def _serialize(self, packet):
        packet.write_u8(self.version)
        packet.write_u24(self.flags)
        packet.write_u16(self.graphics_mode)

        for i in range(3):
            packet.write_u16(self.op_color[i])

    @classmethod
    def _deserialize(cls, io):
        version = io.read_u8()
        flags = io.read_u24()

        graphics_mode = io.read_u16()
        op_color = []
        for i in range(3):
            op_color.append(io.read_u16())

        return cls(version, flags, graphics_mode, op_color)


class BoxPayloadDREF(BoxContainer):
    def __init__(self, version=0, boxes=[]):
        self.version = version
        self.boxes = boxes

    @property
    def size(self):
        size = 1+3+4

        for box in self.boxes:
            size += box.size

        return size

    def _serialize(self, packet):
        packet.write_u8(self.version)
        packet.write_u24(0) # Reserved
        packet.write_u32(len(self.boxes))

        for box in self.boxes:
            box.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        version = io.read_u8()
        flags = io.read_u24()

        entry_count = io.read_u32()
        boxes = []
        for i in range(entry_count):
            box = Box.deserialize(io=io)
            boxes.append(box)

        return cls(version, boxes)

class BoxPayloadURL(BoxPayload):
    def __init__(self, version=0, flags=1):
        self.version = version
        self.flags = flags

    @property
    def size(self):
        return 4

    def _serialize(self, packet):
        packet.write_u8(self.version)
        packet.write_u24(self.flags)

    @classmethod
    def _deserialize(cls, io):
        version = io.read_u8()
        flags = io.read_u24()

        return cls(version, flags)

class BoxPayloadSTSD(BoxContainer):
    def __init__(self, version=0, descriptions=[]):
        self.version = version
        self.descriptions = descriptions

    @property
    def size(self):
        size = 4+4

        for description in self.descriptions:
            size += description.size

        return size

    @property
    def boxes(self):
        return self.descriptions

    def _serialize(self, packet):
        packet.write_u8(self.version)
        packet.write_u24(0) # Reserved
        packet.write_u32(len(self.descriptions))

        for description in self.descriptions:
            description.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        version = io.read_u8()
        flags = io.read_u24()
        count = io.read_u32()

        descriptions = []
        for i in range(count):
            box = Box.deserialize(io=io)
            descriptions.append(box)

        return cls(version, descriptions)

class BoxPayloadVisualSample(BoxContainer):
    def __init__(self, data_reference_index=0, width=0, height=0,
                 horiz_resolution=0.0, vert_resolution=0.0, frame_count=0,
                 compressor_name="", depth=0, boxes=[]):
        self.data_reference_index = data_reference_index
        self.width = width
        self.height = height
        self.horiz_resolution = horiz_resolution
        self.vert_resolution = vert_resolution
        self.frame_count = frame_count
        self.compressor_name = compressor_name
        slef.depth = depth
        self.boxes = boxes

    @property
    def size(self):
        return 4

    def _serialize(self, packet):
        packet.write_u8(self.version)
        packet.write_u24(self.flags)

    @classmethod
    def _deserialize(cls, io):
        for i in range(4):
            io.read_u8()


        return cls(version, flags)




class BoxPayloadMDAT(RawPayload):
    def __repr__(self):
        return "<BoxPayloadMDAT size={0}>".format(self.size)

class BoxPayloadSKIP(RawPayload):
    def __repr__(self):
        return "<BoxPayloadSKIP size={0}>".format(self.size)

class BoxPayloadFREE(RawPayload):
    def __repr__(self):
        return "<BoxPayloadFREE size={0}>".format(self.size)


class BoxPayloadABST(BoxPayload):
    class Flags(Union):
        class Bits(BigEndianStructure):
            _fields_ = [("profile", c_uint8, 2),
                        ("live", c_uint8, 1),
                        ("update", c_uint8, 1),
                        ("reserved", c_uint8, 4)]

        _fields_ = [("bit", Bits), ("byte", c_uint8)]

    def __init__(self, version, bootstrap_info_version, profile, live, update,
                       time_scale, current_media_time, smpte_time_code_offset,
                       movie_identifier, server_entry_table, quality_entry_table,
                       drm_data, metadata, segment_run_table_entries,
                       fragment_run_table_entries):
        self.version = version
        self.bootstrap_info_version = bootstrap_info_version
        self.flags = self.Flags()
        self.flags.bit.profile = profile
        self.flags.bit.live = live
        self.flags.bit.update = update
        self.flags.bit.reserved = 0
        self.time_scale = time_scale
        self.current_media_time = current_media_time
        self.smpte_time_code_offset = smpte_time_code_offset
        self.movie_identifier = movie_identifier
        self.server_entry_table = server_entry_table
        self.quality_entry_table = quality_entry_table
        self.drm_data = drm_data
        self.metadata = metadata
        self.segment_run_table_entries = segment_run_table_entries
        self.fragment_run_table_entries = fragment_run_table_entries

    profile = flagproperty("flags", "profile")
    update = flagproperty("flags", "update", True)
    live = flagproperty("flags", "live", True)

    @property
    def size(self):
        size = 1+3+4+1+4+8+8
        size += len(self.movie_identifier) + 1

        size += 1
        for server in self.server_entry_table:
            size += len(server) + 1

        size += 1
        for quality_entry in self.quality_entry_table:
            size += len(quality_entry) + 1

        size += len(self.drm_data) + 1
        size += len(self.metadata) + 1

        size += 1
        for segment_run_table in self.segment_run_table_entries:
            size += segment_run_table.size

        size += 1
        for fragment_run_table in self.fragment_run_table_entries:
            size += fragment_run_table.size

        return size

    def _serialize(self, packet):
        packet.write_u8(self.version)
        packet.write_u24(0) # Reserved
        packet.write_u32(self.bootstrap_info_version)
        packet.write_u8(self.flags.byte)
        packet.write_u32(self.time_scale)
        packet.write_u64(self.current_media_time)
        packet.write_u64(self.smpte_time_code_offset)
        packet.write_string(self.movie_identifier)

        packet.write_u8(len(self.server_entry_table))
        for server_entry in self.server_entry_table:
            packet.write_string(server_entry)

        packet.write_u8(len(self.quality_entry_table))
        for quality_entry in self.quality_entry_table:
            packet.write_string(quality_entry)

        packet.write_string(self.drm_data)
        packet.write_string(self.metadata)

        packet.write_u8(len(self.segment_run_table_entries))
        for segment_run_table in self.segment_run_table_entries:
            segment_run_table.serialize(packet)

        packet.write_u8(len(self.fragment_run_table_entries))
        for fragment_run_table in self.fragment_run_table_entries:
            fragment_run_table.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        version = io.read_u8()
        io.read_u24() # Reserved
        bootstrap_info_version = io.read_u32()
        flags = cls.Flags()
        flags.byte = io.read_u8()
        time_scale = io.read_u32()
        current_media_time = io.read_u64()
        smpte_time_code_offset = io.read_u64()
        movie_identifier = io.read_string()

        server_entry_table = []
        server_entry_count = io.read_u8()

        for i in range(server_entry_count):
            server_entry = io.read_string()
            server_entry_table.append(server)

        quality_entry_table = []
        quality_entry_count = io.read_u8()

        for i in range(quality_entry_count):
            quality_entry = io.read_string()
            quality_entry_table.append(quality)

        drm_data = io.read_string()
        metadata = io.read_string()

        segment_run_table_entries = []
        segment_run_table_count = io.read_u8()

        for i in range(segment_run_table_count):
            segment_run_table = Box.deserialize(io=io)
            segment_run_table_entries.append(segment_run_table)

        fragment_run_table_entries = []
        fragment_run_table_count = io.read_u8()

        for i in range(fragment_run_table_count):
            fragment_run_table = Box.deserialize(io=io)
            fragment_run_table_entries.append(fragment_run_table)

        return cls(version, bootstrap_info_version, flags.bit.profile,
                   flags.bit.live, flags.bit.update, time_scale,
                   current_media_time, smpte_time_code_offset, movie_identifier,
                   server_entry_table, quality_entry_table, drm_data,
                   metadata, segment_run_table_entries, fragment_run_table_entries)


class SegmentRunEntry(BoxPayload):
    def __init__(self, first_segment, fragments_per_segment):
        self.first_segment = first_segment
        self.fragments_per_segment = fragments_per_segment

    @property
    def size(self):
        return 8

    def _serialize(self, packet):
        packet.write_u32(self.first_segment)
        packet.write_u32(self.fragments_per_segment)

    @classmethod
    def _deserialize(cls, io):
        first_segment = io.read_u32()
        fragments_per_segment = io.read_u32()

        return cls(first_segment, fragments_per_segment)


class BoxPayloadASRT(BoxPayload):
    def __init__(self, version, flags, quality_segment_url_modifiers,
                 segment_run_entry_table):
        self.version = version
        self.flags = flags
        self.quality_segment_url_modifiers = quality_segment_url_modifiers
        self.segment_run_entry_table = segment_run_entry_table

    @property
    def size(self):
        size = 1+3+1+4

        for quality in self.quality_segment_url_modifiers:
            size += len(quality) + 1

        for segment_run_entry in self.segment_run_entry_table:
            size += segment_run_entry.size

        return size

    def _serialize(self, packet):
        packet.write_u8(self.version)
        packet.write_u24(self.flags)
        packet.write_u8(len(self.quality_segment_url_modifiers))

        for quality in self.quality_segment_url_modifiers:
            packet.write_string(quality)

        packet.write_u32(len(self.segment_run_entry_table))
        for segment_run_entry in self.segment_run_entry_table:
            segment_run_entry.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        version = io.read_u8()
        flags = io.read_u24()

        quality_segment_url_modifiers = []
        quality_entry_count = io.read_u8()

        for i in range(quality_entry_count):
            quality = io.read_string()
            quality_segment_url_modifiers.append(quality)

        segment_run_entry_count = io.read_u32()
        segment_run_entry_table = []

        for i in range(segment_run_entry_count):
            segment_run_entry = SegmentRunEntry.deserialize(io=io)
            segment_run_entry_table.append(segment_run_entry)

        return cls(version, flags, quality_segment_url_modifiers,
                   segment_run_entry_table)


class FragmentRunEntry(BoxPayload):
    def __init__(self, first_fragment, first_fragment_timestamp,
                 fragment_duration, discontinuity_indicator):
        self.first_fragment = first_fragment
        self.first_fragment_timestamp = first_fragment_timestamp
        self.fragment_duration = fragment_duration
        self.discontinuity_indicator = discontinuity_indicator

    @property
    def size(self):
        size = 4+8+4

        if self.fragment_duration == 0:
            size += 1

        return size

    def _serialize(self, packet):
        packet.write_u32(self.first_fragment)
        packet.write_u64(self.first_fragment_timestamp)
        packet.write_u32(self.fragment_duration)

        if self.fragment_duration == 0:
            packet.write_u8(self.discontinuity_indicator)

    @classmethod
    def _deserialize(cls, io):
        first_fragment = io.read_u32()
        first_fragment_timestamp = io.read_u64()
        fragment_duration = io.read_u32()

        if fragment_duration == 0:
            discontinuity_indicator = io.read_u8()
        else:
            discontinuity_indicator = None

        return cls(first_fragment, first_fragment_timestamp,
                   fragment_duration, discontinuity_indicator)


class BoxPayloadAFRT(BoxPayload):
    def __init__(self, version, flags, time_scale,
                 quality_segment_url_modifiers,
                 fragment_run_entry_table):
        self.version = version
        self.flags = flags
        self.time_scale = time_scale
        self.quality_segment_url_modifiers = quality_segment_url_modifiers
        self.fragment_run_entry_table = fragment_run_entry_table

    @property
    def size(self):
        size = 1+3+4+1+4

        for quality in self.quality_segment_url_modifiers:
            size += len(quality) + 1

        for fragment_run_entry in self.fragment_run_entry_table:
            size += fragment_run_entry.size

        return size

    def _serialize(self, packet):
        packet.write_u8(self.version)
        packet.write_u24(self.flags)
        packet.write_u32(self.time_scale)
        packet.write_u8(len(self.quality_segment_url_modifiers))

        for quality in self.quality_segment_url_modifiers:
            packet.write_string(quality)

        packet.write_u32(len(self.fragment_run_entry_table))
        for fragment_run_entry in self.fragment_run_entry_table:
            fragment_run_entry.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        version = io.read_u8()
        flags = io.read_u24()
        time_scale = io.read_u32()

        quality_segment_url_modifiers = []
        quality_entry_count = io.read_u8()

        for i in range(quality_entry_count):
            quality = io.read_string()
            quality_segment_url_modifiers.append(quality)

        fragment_run_entry_count = io.read_u32()
        fragment_run_entry_table = []

        for i in range(fragment_run_entry_count):
            fragment_run_entry = FragmentRunEntry.deserialize(io=io)
            fragment_run_entry_table.append(fragment_run_entry)

        return cls(version, flags, time_scale,
                   quality_segment_url_modifiers,
                   fragment_run_entry_table)


class BoxPayloadMVEX(BoxContainer):
    pass

class BoxPayloadMFRA(BoxContainer):
    pass

class BoxPayloadTRAK(BoxContainer):
    pass

class BoxPayloadMDIA(BoxContainer):
    pass

class BoxPayloadMINF(BoxContainer):
    pass

class BoxPayloadSTBL(BoxContainer):
    pass

class BoxPayloadMOOV(BoxContainer):
    pass

class BoxPayloadMOOF(BoxContainer):
    pass

class BoxPayloadMETA(BoxContainer):
    pass


class BoxPayloadDINF(BoxContainerSingle):
    pass

PayloadTypes = {
    "ftyp": BoxPayloadFTYP,
    "mvhd": BoxPayloadMVHD,
    "trex": BoxPayloadTREX,
    "tkhd": BoxPayloadTKHD,
    "mdhd": BoxPayloadMDHD,
    "hdlr": BoxPayloadHDLR,
    "vmhd": BoxPayloadVMHD,
    "dref": BoxPayloadDREF,
    "url":  BoxPayloadURL,
    "stsd": BoxPayloadSTSD,
    "mdat": BoxPayloadMDAT,

    "abst": BoxPayloadABST,
    "asrt": BoxPayloadASRT,
    "afrt": BoxPayloadAFRT,
    "skip": BoxPayloadSKIP,
    "free": BoxPayloadFREE,

    # Containers
    "moov": BoxPayloadMOOV,
    "moof": BoxPayloadMOOF,
    "mvex": BoxPayloadMVEX,
    "mdia": BoxPayloadMDIA,
    "minf": BoxPayloadMINF,
    "meta": BoxPayloadMETA,
    "mfra": BoxPayloadMFRA,
    "stbl": BoxPayloadSTBL,
    "trak": BoxPayloadTRAK,
    "dinf": BoxPayloadDINF,
}

