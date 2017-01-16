from ctypes import BigEndianStructure, Union, c_uint8, c_uint16, c_uint32
from io import BytesIO

from .compat import *
from .error import *
from .packet import *
from .types import *
from .util import *


class Box(Packet):
    exception = F4VError

    def __init__(self, type, payload, extended_size=False):
        self.type = type
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
    def _deserialize(cls, io, strict=False, raw_payload=False):
        size = U32BE.read(io)
        type_ = FourCC.read(io)
        header_size = 8
        extended_size = False

        if size == 1:
            size = U64BE.read(io)
            header_size += 8
            extended_size = True

        if size == 0:
            data = io.read()
        else:
            data = chunked_read(io, size - header_size, exception=F4VError)

        if type_ in PayloadTypes and not raw_payload:
            payloadcls = PayloadTypes[type_]
            payloadio = BytesIO(data)
            payload = payloadcls.deserialize(payloadio)
        else:
            payload = RawPayload(data)

        box = cls(type_, payload, extended_size)

        if strict and box.size != size:
            raise F4VError("Data size mismatch when deserialising tag")

        return box

    def _serialize(self, packet):
        size = self.payload.size

        if size > 0xFFFFFFFF or self.extended_size:
            packet += U32BE(1)
        else:
            packet += U32BE(size + 8)

        packet += FourCC(self.type)

        if size > 0xFFFFFFFF or self.extended_size:
            packet += U64BE(size + 16)

        if isinstance(self.payload, BoxPayload):
            self.payload.serialize(packet)
        else:
            packetwrite(self.payload)


class BoxPayload(Packet):
    exception = F4VError

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

        while True:
            try:
                box = Box.deserialize(io)
            except IOError:
                break

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
        box = Box.deserialize(io)

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
        packet += self.data


class BoxPayloadFTYP(BoxPayload):
    def __init__(self, major_brand="f4v", minor_version=0,
                 compatible_brands=["isom", "mp42", "m4v"]):
        self.major_brand = major_brand
        self.minor_version = minor_version
        self.compatible_brands = compatible_brands

    @property
    def size(self):
        return 4 + 4 + (len(self.compatible_brands) * 4)

    def _serialize(self, packet):
        packet += FourCC(self.major_brand)
        packet += U32BE(self.minor_version)

        for brand in self.compatible_brands:
            packet += FourCC(brand)

    @classmethod
    def _deserialize(cls, io):
        major_brand = FourCC.read(io)
        minor_version = U32BE.read(io)
        compatible_brands = []

        while True:
            try:
                brand = FourCC.read(io)
            except IOError:
                break

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
        size = 1 + 3 + 4 + 4 + 2 + 2 + 4 + 4 + (9 * 4) + (6 * 4) + 4

        if self.version == 1:
            size += 3 * 8
        else:
            size += 3 * 4

        return size

    def _serialize(self, packet):
        packet += U8(self.version)
        packet += U24BE(0)  # Reserved

        packet += U3264(self.creation_time, self.version)
        packet += U3264(self.modification_time, self.version)
        packet += U32BE(self.time_scale)
        packet += U3264(self.duration, self.version)

        packet += S16BE_16(self.rate)
        packet += S8_8BE(self.volume)

        packet += U16BE(0)  # Reserved
        packet += U32BE(0)  # Reserved
        packet += U32BE(0)  # Reserved

        for m in self.matrix:
            packet += U32BE(m)

        for i in range(6):
            packet += U32BE(0)  # Reserved

        packet += U32BE(self.next_track_id)

    @classmethod
    def _deserialize(cls, io):
        version = U8.read(io)
        U24BE.read(io)  # Reserved

        creation_time = U3264.read(io, version)
        modification_time = U3264.read(io, version)
        time_scale = U32BE.read(io)
        duration = U3264.read(io, version)

        rate = S16_16.read(io)
        volume = S8_8BE.read(io)

        U16BE.read(io)  # Reserved
        U32BE.read(io)  # Reserved
        U32BE.read(io)  # Reserved

        matrix = []
        for i in range(9):
            matrix.append(U32BE.read(io))

        for i in range(6):
            U32BE.read(io)  # Reserved

        next_track_id = U32BE.read(io)

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
        self.flags.bit.reserved = 0  # Reserved
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
        packet += U32BE(self.flags.byte)

    @classmethod
    def _deserialize(cls, io):
        flags = cls.Flags()
        flags.byte = U32BE.read(io)

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
        return 1 + 3 + 4 + 4 + 4 + 4 + self.default_sample_flags.size

    def _serialize(self, packet):
        packet += U8(self.version)
        packet += U24BE(0)  # Reserved
        packet += U32BE(self.track_id)
        packet += U32BE(self.default_sample_description_index)
        packet += U32BE(self.default_sample_duration)
        packet += U32BE(self.default_sample_size)
        self.default_sample_flags.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        version = U8.read(io)
        flags = U24BE.read(io)
        track_id = U32BE.read(io)
        default_sample_description_index = U32BE.read(io)
        default_sample_duration = U32BE.read(io)
        default_sample_size = U32BE.read(io)
        default_sample_flags = SampleFlags.deserialize(io)

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
        size = 1 + 3 + 4 + 4 + 4 + 4 + 4 + (4 * 2) + 2 + 2 + 2 + 2 + (9 * 4) + 4 + 4

        if self.version == 1:
            size += 4 * 3

        return size

    def _serialize(self, packet):
        packet += U8(self.version)
        packet += U24BE(self.flags)

        packet += U3264(self.creation_time, self.version)
        packet += U3264(self.modification_time, self.version)
        packet += U32BE(self.track_id)
        packet += U32BE(0)  # Reserved
        packet += U3264(self.duration, self.version)

        for i in range(2):
            packet += U32BE(0)  # Reserved

        packet += S16BE(self.layer)
        packet += S16BE(self.alternate_group)
        packet += S8_8BE(self.volume)
        packet += U16BE(0)  # Reserved

        for i in range(9):
            packet += U32BE(self.transform_matrix[i])

        packet += S16BE_16(self.width)
        packet += S16BE_16(self.height)

    @classmethod
    def _deserialize(cls, io):
        version = U8.read(io)
        flags = U24BE.read(io)

        creation_time = U3264.read(io, version)
        modification_time = U3264.read(io, version)
        track_id = U32BE.read(io)
        U32BE.read(io)  # Reserved
        duration = U3264.read(io, version)

        for i in range(2):
            U32BE.read(io)  # Reserved

        layer = S16BE.read(io)
        alternate_group = S16BE.read(io)
        volume = S8_8BE.read(io)
        U16BE.read(io)  # Reserved

        transform_matrix = []
        for i in range(9):
            transform_matrix.append(S32BE.read(io))

        width = S16_16.read(io)
        height = S16_16.read(io)

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
        size = 1 + 3 + 4 + 4 + 4 + 4 + 2 + 2

        if self.version == 1:
            size += 4 * 3

        return size

    def _serialize(self, packet):
        packet += U8(self.version)
        packet += U24BE(0)  # Reserved

        packet += U3264(self.creation_time, self.version)
        packet += U3264(self.modification_time, self.version)
        packet += U32BE(self.time_scale)
        packet += U3264(self.duration, self.version)

        packet += S16BE(iso639_to_lang(self.language))
        packet += U16BE(0)  # Reserved

    @classmethod
    def _deserialize(cls, io):
        version = U8.read(io)
        U24BE.read(io)  # Reserved

        creation_time = U3264.read(io, version)
        modification_time = U3264.read(io, version)
        time_scale = U32BE.read(io)
        duration = U3264.read(io, version)

        language = lang_to_iso639(U16BE.read(io))
        U16BE.read(io)  # Reserved

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
        size = 1 + 3 + 4 + 4 + (3 * 4)
        size += len(self.name)

        return size

    def _serialize(self, packet):
        packet += U8(self.version)
        packet += U24BE(0)  # Reserved
        packet += U32BE(self.predefined)
        packet += FourCC(self.handler_type)

        for i in range(3):
            packet += U32BE(0)  # Reserved

        #packet += self.name.encode("utf8", "ignore")
        packet += CString(self.name)

    @classmethod
    def _deserialize(cls, io):
        version = U8.read(io)
        flags = U24BE.read(io)  # Reserved

        predefined = U32BE.read(io)
        handler_type = FourCC.read(io)

        for i in range(3):
            U32BE.read(io)  # Reserved

        name = CString.read(io)

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
        return 1 + 3 + 2 + (3 * 2)

    def _serialize(self, packet):
        packet += U8(self.version)
        packet += U24BE(self.flags)
        packet += U16BE(self.graphics_mode)

        for i in range(3):
            packet += U16BE(self.op_color[i])

    @classmethod
    def _deserialize(cls, io):
        version = U8.read(io)
        flags = U24BE.read(io)

        graphics_mode = U16BE.read(io)
        op_color = []
        for i in range(3):
            op_color.append(U16BE.read(io))

        return cls(version, flags, graphics_mode, op_color)


class BoxPayloadDREF(BoxContainer):
    def __init__(self, version=0, boxes=[]):
        self.version = version
        self.boxes = boxes

    @property
    def size(self):
        size = 1 + 3 + 4

        for box in self.boxes:
            size += box.size

        return size

    def _serialize(self, packet):
        packet += U8(self.version)
        packet += U24BE(0)  # Reserved
        packet += U32BE(len(self.boxes))

        for box in self.boxes:
            box.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        version = U8.read(io)
        flags = U24BE.read(io)

        entry_count = U32BE.read(io)
        boxes = []
        for i in range(entry_count):
            box = Box.deserialize(io)
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
        packet += U8(self.version)
        packet += U24BE(self.flags)

    @classmethod
    def _deserialize(cls, io):
        version = U8.read(io)
        flags = U24BE.read(io)

        return cls(version, flags)


class BoxPayloadSTSD(BoxContainer):
    def __init__(self, version=0, descriptions=[]):
        self.version = version
        self.descriptions = descriptions

    @property
    def size(self):
        size = 4 + 4

        for description in self.descriptions:
            size += description.size

        return size

    @property
    def boxes(self):
        return self.descriptions

    def _serialize(self, packet):
        packet += U8(self.version)
        packet += U24BE(0)  # Reserved
        packet += U32BE(len(self.descriptions))

        for description in self.descriptions:
            description.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        version = U8.read(io)
        flags = U24BE.read(io)
        count = U32BE.read(io)

        descriptions = []
        for i in range(count):
            box = Box.deserialize(io)
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
        packet += U8(self.version)
        packet += U24BE(self.flags)

    @classmethod
    def _deserialize(cls, io):
        for i in range(4):
            U8.read(io)

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
        size = 1 + 3 + 4 + 1 + 4 + 8 + 8
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
        packet += U8(self.version)
        packet += U24BE(0)  # Reserved
        packet += U32BE(self.bootstrap_info_version)
        packet += U8(self.flags.byte)
        packet += U32BE(self.time_scale)
        packet += U64BE(self.current_media_time)
        packet += U64BE(self.smpte_time_code_offset)
        packet += CString(self.movie_identifier)

        packet += U8(len(self.server_entry_table))
        for server_entry in self.server_entry_table:
            packet += CString(server_entry)

        packet += U8(len(self.quality_entry_table))
        for quality_entry in self.quality_entry_table:
            packet += CString(quality_entry)

        packet += CString(self.drm_data)
        packet += CString(self.metadata)

        packet += U8(len(self.segment_run_table_entries))
        for segment_run_table in self.segment_run_table_entries:
            segment_run_table.serialize(packet)

        packet += U8(len(self.fragment_run_table_entries))
        for fragment_run_table in self.fragment_run_table_entries:
            fragment_run_table.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        version = U8.read(io)
        U24BE.read(io)  # Reserved
        bootstrap_info_version = U32BE.read(io)
        flags = cls.Flags()
        flags.byte = U8.read(io)
        time_scale = U32BE.read(io)
        current_media_time = U64BE.read(io)
        smpte_time_code_offset = U64BE.read(io)
        movie_identifier = CString.read(io)

        server_entry_table = []
        server_entry_count = U8.read(io)

        for i in range(server_entry_count):
            server_entry = CString.read(io)
            server_entry_table.append(server_entry)

        quality_entry_table = []
        quality_entry_count = U8.read(io)

        for i in range(quality_entry_count):
            quality_entry = CString.read(io)
            quality_entry_table.append(quality_entry)

        drm_data = CString.read(io)
        metadata = CString.read(io)

        segment_run_table_entries = []
        segment_run_table_count = U8.read(io)

        for i in range(segment_run_table_count):
            segment_run_table = Box.deserialize(io)
            segment_run_table_entries.append(segment_run_table)

        fragment_run_table_entries = []
        fragment_run_table_count = U8.read(io)

        for i in range(fragment_run_table_count):
            fragment_run_table = Box.deserialize(io)
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
        packet += U32BE(self.first_segment)
        packet += U32BE(self.fragments_per_segment)

    @classmethod
    def _deserialize(cls, io):
        first_segment = U32BE.read(io)
        fragments_per_segment = U32BE.read(io)

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
        size = 1 + 3 + 1 + 4

        for quality in self.quality_segment_url_modifiers:
            size += len(quality) + 1

        for segment_run_entry in self.segment_run_entry_table:
            size += segment_run_entry.size

        return size

    def _serialize(self, packet):
        packet += U8(self.version)
        packet += U24BE(self.flags)
        packet += U8(len(self.quality_segment_url_modifiers))

        for quality in self.quality_segment_url_modifiers:
            packet += CString(quality)

        packet += U32BE(len(self.segment_run_entry_table))
        for segment_run_entry in self.segment_run_entry_table:
            segment_run_entry.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        version = U8.read(io)
        flags = U24BE.read(io)

        quality_segment_url_modifiers = []
        quality_entry_count = U8.read(io)

        for i in range(quality_entry_count):
            quality = CString.read(io)
            quality_segment_url_modifiers.append(quality)

        segment_run_entry_count = U32BE.read(io)
        segment_run_entry_table = []

        for i in range(segment_run_entry_count):
            segment_run_entry = SegmentRunEntry.deserialize(io)
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
        size = 4 + 8 + 4

        if self.fragment_duration == 0:
            size += 1

        return size

    def _serialize(self, packet):
        packet += U32BE(self.first_fragment)
        packet += U64BE(self.first_fragment_timestamp)
        packet += U32BE(self.fragment_duration)

        if self.fragment_duration == 0:
            packet += U8(self.discontinuity_indicator)

    @classmethod
    def _deserialize(cls, io):
        first_fragment = U32BE.read(io)
        first_fragment_timestamp = U64BE.read(io)
        fragment_duration = U32BE.read(io)

        if fragment_duration == 0:
            discontinuity_indicator = U8.read(io)
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
        size = 1 + 3 + 4 + 1 + 4

        for quality in self.quality_segment_url_modifiers:
            size += len(quality) + 1

        for fragment_run_entry in self.fragment_run_entry_table:
            size += fragment_run_entry.size

        return size

    def _serialize(self, packet):
        packet += U8(self.version)
        packet += U24BE(self.flags)
        packet += U32BE(self.time_scale)
        packet += U8(len(self.quality_segment_url_modifiers))

        for quality in self.quality_segment_url_modifiers:
            packet += CString(quality)

        packet += U32BE(len(self.fragment_run_entry_table))
        for fragment_run_entry in self.fragment_run_entry_table:
            fragment_run_entry.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        version = U8.read(io)
        flags = U24BE.read(io)
        time_scale = U32BE.read(io)

        quality_segment_url_modifiers = []
        quality_entry_count = U8.read(io)

        for i in range(quality_entry_count):
            quality = CString.read(io)
            quality_segment_url_modifiers.append(quality)

        fragment_run_entry_count = U32BE.read(io)
        fragment_run_entry_table = []

        for i in range(fragment_run_entry_count):
            fragment_run_entry = FragmentRunEntry.deserialize(io)
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
    "url": BoxPayloadURL,
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
