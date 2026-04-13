use protobuf::Enum;
use crate::{attribute_proto::AttributeType, AttributeProto, GraphProto, SparseTensorProto, TensorProto, TypeProto};
use crate::tensor_proto::DataType;

/// Typed onnx attribute value
pub enum AttributeValue<'a> {
    Unknown(i32),
    Float32(f32),
    Float32s(&'a [f32]),
    Integer64(i64),
    Integer64s(&'a [i64]),
    String(&'a [u8]),
    Strings(&'a [Vec<u8>]),
    Type(&'a TypeProto),
    Types(&'a [TypeProto]),
    Graph(&'a GraphProto),
    Graphs(&'a [GraphProto]),
    Tensor(&'a TensorProto),
    Tensors(&'a [TensorProto]),
    SparseTensor(&'a SparseTensorProto),
    SparseTensors(&'a [SparseTensorProto]),
}

impl AttributeProto {
    /// Convert to typed value
    pub fn as_value(&self) -> AttributeValue<'_> {
        match self.type_.enum_value() {
            Ok(o) => match o {
                AttributeType::UNDEFINED => AttributeValue::Unknown(0),
                AttributeType::FLOAT => AttributeValue::Float32(self.f),
                AttributeType::FLOATS => AttributeValue::Float32s(&self.floats),
                AttributeType::INT => AttributeValue::Integer64(self.i),
                AttributeType::INTS => AttributeValue::Integer64s(&self.ints),
                AttributeType::STRING => AttributeValue::String(&self.s),
                AttributeType::STRINGS => AttributeValue::Strings(&self.strings),
                AttributeType::TENSOR => match &self.t.0 {
                    Some(s) => AttributeValue::Tensor(s),
                    None => unreachable!(),
                },
                AttributeType::TENSORS => AttributeValue::Tensors(&self.tensors),
                AttributeType::GRAPH => match &self.g.0 {
                    Some(s) => AttributeValue::Graph(s),
                    None => unreachable!(),
                },
                AttributeType::GRAPHS => AttributeValue::Graphs(&self.graphs),
                AttributeType::SPARSE_TENSOR => match &self.sparse_tensor.0 {
                    Some(s) => AttributeValue::SparseTensor(s),
                    None => unreachable!(),
                },
                AttributeType::SPARSE_TENSORS => AttributeValue::SparseTensors(&self.sparse_tensors),
                AttributeType::TYPE_PROTO => match &self.tp.0 {
                    Some(s) => AttributeValue::Type(s),
                    None => unreachable!(),
                },
                AttributeType::TYPE_PROTOS => AttributeValue::Types(&self.type_protos),
            },
            Err(e) => AttributeValue::Unknown(e),
        }
    }
}

/// Typed onnx tensor value
pub enum TensorValue<'p> {
    Unknown(i32),
    Float32(&'p [f32]),
    Float64(&'p [f64]),
    Unsigned32(&'p [u32]),
    Unsigned64(&'p [u64]),
    Integer8(&'p [i8]),
    Integer16(&'p [i16]),
    Integer32(&'p [i32]),
    Integer64(&'p [i64]),
}

impl TensorProto {
    /// Convert to typed value
    pub fn as_value(&self) -> TensorValue<'_> {
        match DataType::from_i32(self.data_type) {
            Some(o) => {
                match o {
                    DataType::UNDEFINED => { TensorValue::Unknown(0) }
                    DataType::FLOAT8E4M3FN => {
                        let _ = &self.int32_data;
                        todo!()
                    }
                    DataType::FLOAT8E4M3FNUZ => {
                        let _ = &self.int32_data;
                        todo!()
                    }
                    DataType::FLOAT8E5M2 => {
                        let _ = &self.int32_data;
                        todo!()
                    }
                    DataType::FLOAT8E5M2FNUZ => {
                        let _ = &self.int32_data;
                        todo!()
                    }
                    DataType::FLOAT16 => {
                        let _ = &self.int32_data;
                        todo!()
                    }
                    DataType::BFLOAT16 => {
                        let _ = &self.int32_data;
                        todo!()
                    }
                    DataType::FLOAT => {
                        TensorValue::Float32(&self.float_data)
                    }
                    DataType::DOUBLE => {
                        TensorValue::Float64(&self.double_data)
                    }
                    DataType::UINT4 => {
                        let _ = &self.int32_data;
                        todo!()
                    }
                    DataType::UINT8 => {
                        let _ = &self.int32_data;
                        todo!()
                    }
                    DataType::UINT16 => {
                        let _ = &self.int32_data;
                        todo!()
                    }
                    DataType::UINT32 => {
                        let u64_slice: &[u64] = &self.uint64_data;
                        let u32_slice: &[u32] = unsafe { core::slice::from_raw_parts(u64_slice.as_ptr() as *const u32, u64_slice.len() * 2) };
                        TensorValue::Unsigned32(u32_slice)
                    }
                    DataType::UINT64 => {
                        TensorValue::Unsigned64(&self.uint64_data)
                    }
                    DataType::BOOL => {
                        let _ = &self.int32_data;
                        todo!()
                    }
                    DataType::INT4 => {
                        let _ = &self.int32_data;
                        todo!()
                    }
                    DataType::INT8 => {
                        let i32_slice: &[i32] = &self.int32_data;
                        let i8_slice: &[i8] = unsafe { core::slice::from_raw_parts(i32_slice.as_ptr() as *const i8, i32_slice.len() * 4) };
                        TensorValue::Integer8(i8_slice)
                    }
                    DataType::INT16 => {
                        let i32_slice: &[i32] = &self.int32_data;
                        let i16_slice: &[i16] = unsafe { core::slice::from_raw_parts(i32_slice.as_ptr() as *const i16, i32_slice.len() * 2) };
                        TensorValue::Integer16(i16_slice)
                    }
                    DataType::INT32 => {
                        TensorValue::Integer32(&self.int32_data)
                    }
                    DataType::INT64 => {
                        TensorValue::Integer64(&self.int64_data)
                    }
                    DataType::COMPLEX64 => {
                        let _ = &self.float_data;
                        todo!()
                    }
                    DataType::COMPLEX128 => {
                        let _ = &self.double_data;
                        todo!()
                    }
                    DataType::STRING => { todo!() }
                }
            }
            None => TensorValue::Unknown(self.data_type),
        }
    }
}
