use proptest::prelude::*;
use llm_provable_computer::{
    decode_state, encode_state, verify_model_against_native, Attention2DMode, HullKvCache,
    Instruction, MachineState, Program, ProgramCompiler, TransformerVmConfig,
};

#[cfg(feature = "burn-model")]
use burn::backend::NdArray;
#[cfg(feature = "burn-model")]
use llm_provable_computer::{
    verify_engines, BurnExecutionRuntime, BurnTransformerVm, ExecutionRuntime, NativeInterpreter,
};

const RANDOM_MEMORY_SIZE: usize = 8;

fn build_random_program(specs: &[(u8, i16, u8, u8)]) -> Program {
    let len = specs.len();
    let mut instructions = specs
        .iter()
        .map(|&(opcode, immediate, address, target)| {
            let address = address % RANDOM_MEMORY_SIZE as u8;
            let target = target % len as u8;
            match opcode % 20 {
                0 => Instruction::Nop,
                1 => Instruction::LoadImmediate(immediate),
                2 => Instruction::Load(address),
                3 => Instruction::Store(address),
                4 => Instruction::AddImmediate(immediate),
                5 => Instruction::AddMemory(address),
                6 => Instruction::SubImmediate(immediate),
                7 => Instruction::SubMemory(address),
                8 => Instruction::MulImmediate(immediate),
                9 => Instruction::MulMemory(address),
                10 => Instruction::AndImmediate(immediate),
                11 => Instruction::AndMemory(address),
                12 => Instruction::OrImmediate(immediate),
                13 => Instruction::OrMemory(address),
                14 => Instruction::XorImmediate(immediate),
                15 => Instruction::XorMemory(address),
                16 => Instruction::CmpImmediate(immediate),
                17 => Instruction::CmpMemory(address),
                18 => Instruction::JumpIfZero(target),
                19 => Instruction::JumpIfNotZero(target),
                _ => unreachable!(),
            }
        })
        .collect::<Vec<_>>();

    if let Some(last) = instructions.last_mut() {
        *last = Instruction::Halt;
    }

    Program::new(instructions, RANDOM_MEMORY_SIZE)
}

proptest! {
    #[test]
    fn state_round_trips_for_all_valid_fields(
        pc in 0u8..=255u8,
        acc in i16::MIN..=i16::MAX,
        sp in 0u8..=255u8,
        zero_flag in any::<bool>(),
        carry_flag in any::<bool>(),
        halted in any::<bool>(),
    ) {
        let state = MachineState {
            pc,
            acc,
            sp,
            zero_flag,
            carry_flag,
            halted,
            memory: vec![0; 4],
        };
        let token = encode_state(&state, 36).unwrap();
        let decoded = decode_state(&token, state.memory.clone()).unwrap();
        prop_assert_eq!(decoded, state);
    }

    #[test]
    fn hull_argmax_matches_bruteforce_random(
        points in prop::collection::vec(
            (-100.0f32..100.0f32, -100.0f32..100.0f32),
            2..64,
        ),
        queries in prop::collection::vec(
            (-10.0f32..10.0f32, -10.0f32..10.0f32),
            1..16,
        ),
    ) {
        let mut cache = HullKvCache::new();
        for (i, &(x, y)) in points.iter().enumerate() {
            // Add small offset to avoid exact duplicate x values
            cache.insert([x + i as f32 * 0.001, y], &[i as f32]);
        }

        for &(qx, qy) in &queries {
            let query = [qx, qy];
            let (fast_pt, _) = cache.query_argmax(query).unwrap();
            let (slow_pt, _) = cache.query_argmax_bruteforce(query).unwrap();

            let fast_score = query[0] * fast_pt.x + query[1] * fast_pt.y;
            let slow_score = query[0] * slow_pt.x + query[1] * slow_pt.y;

            prop_assert!(
                (fast_score - slow_score).abs() < 1e-2,
                "query={query:?}, fast_score={fast_score}, slow_score={slow_score}"
            );
        }
    }

    #[test]
    fn hull_argmax_matches_bruteforce_monotonic(
        values in prop::collection::vec(-1000.0f32..1000.0f32, 2..128),
        queries in prop::collection::vec(
            (-10.0f32..10.0f32, -10.0f32..10.0f32),
            1..16,
        ),
    ) {
        let mut cache = HullKvCache::new();
        for (i, &y) in values.iter().enumerate() {
            cache.insert([i as f32, y], &[y]);
        }

        prop_assert!(cache.is_monotonic());

        for &(qx, qy) in &queries {
            let query = [qx, qy];
            let (fast_pt, _) = cache.query_argmax(query).unwrap();
            let (slow_pt, _) = cache.query_argmax_bruteforce(query).unwrap();

            let fast_score = query[0] * fast_pt.x + query[1] * fast_pt.y;
            let slow_score = query[0] * slow_pt.x + query[1] * slow_pt.y;

            prop_assert!(
                (fast_score - slow_score).abs() < 1e-2,
                "query={query:?}, fast_score={fast_score}, slow_score={slow_score}"
            );
        }
    }

    #[test]
    fn hull_size_bounded_by_total(
        insertions in prop::collection::vec(
            (-50.0f32..50.0f32, -50.0f32..50.0f32),
            1..100,
        ),
    ) {
        let mut cache = HullKvCache::new();
        for (i, &(x, y)) in insertions.iter().enumerate() {
            cache.insert([x, y], &[i as f32]);
            prop_assert!(cache.hull_size() <= cache.total_size());
        }
    }

    #[test]
    fn monotonic_insert_preserves_flag(
        values in prop::collection::vec(-1000.0f32..1000.0f32, 1..200),
    ) {
        let mut cache = HullKvCache::new();
        for (i, &y) in values.iter().enumerate() {
            cache.insert([i as f32, y], &[y]);
        }
        prop_assert!(cache.is_monotonic());
    }

    #[test]
    fn non_monotonic_insert_clears_flag(
        values in prop::collection::vec(-100.0f32..100.0f32, 3..50),
    ) {
        let mut cache = HullKvCache::new();
        // Insert in reverse order to guarantee non-monotonic
        for (i, &y) in values.iter().enumerate() {
            let x = (values.len() - i) as f32;
            cache.insert([x, y], &[y]);
        }
        // With 3+ values in reverse x order, monotonic must be false
        prop_assert!(!cache.is_monotonic());

        // But queries should still be correct
        for &y in &values {
            let query = [1.0, y.signum()];
            let (fast_pt, _) = cache.query_argmax(query).unwrap();
            let (slow_pt, _) = cache.query_argmax_bruteforce(query).unwrap();

            let fast_score = query[0] * fast_pt.x + query[1] * fast_pt.y;
            let slow_score = query[0] * slow_pt.x + query[1] * slow_pt.y;

            prop_assert!(
                (fast_score - slow_score).abs() < 1e-2,
                "query={query:?}, fast_score={fast_score}, slow_score={slow_score}"
            );
        }
    }

    #[test]
    fn softmax_query_stays_within_inserted_value_range(
        values in prop::collection::vec(-1000.0f32..1000.0f32, 2..64),
        temperature in 0.1f32..20.0f32,
    ) {
        let mut cache = HullKvCache::new();
        for (step, &value) in values.iter().enumerate() {
            cache.insert([step as f32, value], &[value]);
        }

        let blended = cache
            .query_value([1.0, 0.0], &Attention2DMode::HardSoftmax { temperature })
            .unwrap()[0];
        let min_value = values.iter().copied().fold(f32::INFINITY, f32::min);
        let max_value = values.iter().copied().fold(f32::NEG_INFINITY, f32::max);

        prop_assert!(blended >= min_value - 1e-3);
        prop_assert!(blended <= max_value + 1e-3);
    }

    #[test]
    fn transformer_matches_native_on_random_average_hard_programs(
        specs in prop::collection::vec((0u8..20u8, any::<i16>(), any::<u8>(), any::<u8>()), 1..24),
        initial_memory in prop::collection::vec(any::<i16>(), RANDOM_MEMORY_SIZE..=RANDOM_MEMORY_SIZE),
        layers in 1usize..=4,
        max_steps in 1usize..=64,
    ) {
        let program = build_random_program(&specs)
            .with_initial_memory(initial_memory)
            .unwrap();
        let model = ProgramCompiler
            .compile_program(
                program,
                TransformerVmConfig {
                    num_layers: layers,
                    attention_mode: Attention2DMode::AverageHard,
                    ..TransformerVmConfig::default()
                },
            )
            .unwrap();

        let comparison = verify_model_against_native(model, max_steps).unwrap();
        prop_assert_eq!(comparison.transformer.final_state, comparison.native.final_state);
        prop_assert_eq!(comparison.transformer.steps, comparison.native.steps);
        prop_assert_eq!(comparison.transformer.halted, comparison.native.halted);
    }

    #[test]
    fn transformer_matches_native_on_random_soft_attention_programs(
        specs in prop::collection::vec((0u8..20u8, any::<i16>(), any::<u8>(), any::<u8>()), 1..24),
        initial_memory in prop::collection::vec(any::<i16>(), RANDOM_MEMORY_SIZE..=RANDOM_MEMORY_SIZE),
        layers in 1usize..=4,
        max_steps in 1usize..=64,
        temperature in 0.1f32..20.0f32,
    ) {
        let program = build_random_program(&specs)
            .with_initial_memory(initial_memory)
            .unwrap();
        let model = ProgramCompiler
            .compile_program(
                program,
                TransformerVmConfig {
                    num_layers: layers,
                    attention_mode: Attention2DMode::HardSoftmax { temperature },
                    ..TransformerVmConfig::default()
                },
            )
            .unwrap();

        let comparison = verify_model_against_native(model, max_steps).unwrap();
        prop_assert_eq!(comparison.transformer.final_state, comparison.native.final_state);
        prop_assert_eq!(comparison.transformer.steps, comparison.native.steps);
        prop_assert_eq!(comparison.transformer.halted, comparison.native.halted);
    }

    #[cfg(feature = "burn-model")]
    #[test]
    fn burn_matches_native_on_random_average_hard_programs(
        specs in prop::collection::vec((0u8..20u8, any::<i16>(), any::<u8>(), any::<u8>()), 1..24),
        initial_memory in prop::collection::vec(any::<i16>(), RANDOM_MEMORY_SIZE..=RANDOM_MEMORY_SIZE),
        layers in 1usize..=4,
        max_steps in 1usize..=64,
    ) {
        type TestBackend = NdArray<f64>;

        let device = Default::default();
        let program = build_random_program(&specs)
            .with_initial_memory(initial_memory)
            .unwrap();
        let model = ProgramCompiler
            .compile_program(
                program,
                TransformerVmConfig {
                    num_layers: layers,
                    attention_mode: Attention2DMode::AverageHard,
                    ..TransformerVmConfig::default()
                },
            )
            .unwrap();
        let burn = BurnTransformerVm::<TestBackend>::from_compiled(&model, &device).unwrap();

        let mut transformer = ExecutionRuntime::new(model.clone(), max_steps);
        let mut native = NativeInterpreter::new(
            model.program().clone(),
            model.config().attention_mode.clone(),
            max_steps,
        );
        let mut burn = BurnExecutionRuntime::new(burn, device, max_steps);

        let verification = verify_engines(&mut [&mut transformer, &mut native, &mut burn]).unwrap();
        prop_assert_eq!(
            &verification.engines[0].result.final_state,
            &verification.engines[2].result.final_state
        );
        prop_assert_eq!(
            &verification.engines[1].result.final_state,
            &verification.engines[2].result.final_state
        );
    }
}
