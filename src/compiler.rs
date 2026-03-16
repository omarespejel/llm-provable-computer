use crate::assembly::parse_program;
use crate::config::TransformerVmConfig;
use crate::error::Result;
use crate::instruction::Program;
use crate::model::TransformerVm;

#[derive(Debug, Default, Clone, Copy)]
pub struct ProgramCompiler;

impl ProgramCompiler {
    pub fn compile_program(
        &self,
        program: Program,
        config: TransformerVmConfig,
    ) -> Result<TransformerVm> {
        TransformerVm::new(config, program)
    }

    pub fn compile_source(
        &self,
        source: &str,
        config: TransformerVmConfig,
    ) -> Result<TransformerVm> {
        let program = parse_program(source)?;
        self.compile_program(program, config)
    }
}
