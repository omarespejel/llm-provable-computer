/// Rescue-Prime hash function for STARK-friendly hashing.
/// Ported from the stark-anatomy Python reference implementation.
use super::field::FieldElement;
use super::multivariate::MPolynomial;
use super::polynomial::Polynomial;

pub struct RescuePrime {
    pub m: usize, // state width
    pub capacity: usize,
    pub n: usize, // number of rounds (N in Python)
    pub alpha: u128,
    pub alphainv: u128,
    pub mds: [[FieldElement; 2]; 2],
    pub mds_inv: [[FieldElement; 2]; 2],
    pub round_constants: Vec<FieldElement>,
}

impl Default for RescuePrime {
    fn default() -> Self {
        Self::new()
    }
}

impl RescuePrime {
    pub fn new() -> Self {
        let fe = |v: u128| FieldElement::new(v);
        RescuePrime {
            m: 2,
            capacity: 1,
            n: 27,
            alpha: 3,
            alphainv: 180331931428153586757283157844700080811,
            mds: [
                [fe(270497897142230380135924736767050121214), fe(4)],
                [fe(270497897142230380135924736767050121205), fe(13)],
            ],
            mds_inv: [
                [
                    fe(210387253332845851216830350818816760948),
                    fe(60110643809384528919094385948233360270),
                ],
                [
                    fe(90165965714076793378641578922350040407),
                    fe(180331931428153586757283157844700080811),
                ],
            ],
            round_constants: vec![
                fe(174420698556543096520990950387834928928),
                fe(109797589356993153279775383318666383471),
                fe(228209559001143551442223248324541026000),
                fe(268065703411175077628483247596226793933),
                fe(250145786294793103303712876509736552288),
                fe(154077925986488943960463842753819802236),
                fe(204351119916823989032262966063401835731),
                fe(57645879694647124999765652767459586992),
                fe(102595110702094480597072290517349480965),
                fe(8547439040206095323896524760274454544),
                fe(50572190394727023982626065566525285390),
                fe(87212354645973284136664042673979287772),
                fe(64194686442324278631544434661927384193),
                fe(23568247650578792137833165499572533289),
                fe(264007385962234849237916966106429729444),
                fe(227358300354534643391164539784212796168),
                fe(179708233992972292788270914486717436725),
                fe(102544935062767739638603684272741145148),
                fe(65916940568893052493361867756647855734),
                fe(144640159807528060664543800548526463356),
                fe(58854991566939066418297427463486407598),
                fe(144030533171309201969715569323510469388),
                fe(264508722432906572066373216583268225708),
                fe(22822825100935314666408731317941213728),
                fe(33847779135505989201180138242500409760),
                fe(146019284593100673590036640208621384175),
                fe(51518045467620803302456472369449375741),
                fe(73980612169525564135758195254813968438),
                fe(31385101081646507577789564023348734881),
                fe(270440021758749482599657914695597186347),
                fe(185230877992845332344172234234093900282),
                fe(210581925261995303483700331833844461519),
                fe(233206235520000865382510460029939548462),
                fe(178264060478215643105832556466392228683),
                fe(69838834175855952450551936238929375468),
                fe(75130152423898813192534713014890860884),
                fe(59548275327570508231574439445023390415),
                fe(43940979610564284967906719248029560342),
                fe(95698099945510403318638730212513975543),
                fe(77477281413246683919638580088082585351),
                fe(206782304337497407273753387483545866988),
                fe(141354674678885463410629926929791411677),
                fe(19199940390616847185791261689448703536),
                fe(177613618019817222931832611307175416361),
                fe(267907751104005095811361156810067173120),
                fe(33296937002574626161968730356414562829),
                fe(63869971087730263431297345514089710163),
                fe(200481282361858638356211874793723910968),
                fe(69328322389827264175963301685224506573),
                fe(239701591437699235962505536113880102063),
                fe(17960711445525398132996203513667829940),
                fe(219475635972825920849300179026969104558),
                fe(230038611061931950901316413728344422823),
                fe(149446814906994196814403811767389273580),
                fe(25535582028106779796087284957910475912),
                fe(93289417880348777872263904150910422367),
                fe(4779480286211196984451238384230810357),
                fe(208762241641328369347598009494500117007),
                fe(34228805619823025763071411313049761059),
                fe(158261639460060679368122984607245246072),
                fe(65048656051037025727800046057154042857),
                fe(134082885477766198947293095565706395050),
                fe(23967684755547703714152865513907888630),
                fe(8509910504689758897218307536423349149),
                fe(232305018091414643115319608123377855094),
                fe(170072389454430682177687789261779760420),
                fe(62135161769871915508973643543011377095),
                fe(15206455074148527786017895403501783555),
                fe(201789266626211748844060539344508876901),
                fe(179184798347291033565902633932801007181),
                fe(9615415305648972863990712807943643216),
                fe(95833504353120759807903032286346974132),
                fe(181975981662825791627439958531194157276),
                fe(267590267548392311337348990085222348350),
                fe(49899900194200760923895805362651210299),
                fe(89154519171560176870922732825690870368),
                fe(265649728290587561988835145059696796797),
                fe(140583850659111280842212115981043548773),
                fe(266613908274746297875734026718148328473),
                fe(236645120614796645424209995934912005038),
                fe(265994065390091692951198742962775551587),
                fe(59082836245981276360468435361137847418),
                fe(26520064393601763202002257967586372271),
                fe(108781692876845940775123575518154991932),
                fe(138658034947980464912436420092172339656),
                fe(45127926643030464660360100330441456786),
                fe(210648707238405606524318597107528368459),
                fe(42375307814689058540930810881506327698),
                fe(237653383836912953043082350232373669114),
                fe(236638771475482562810484106048928039069),
                fe(168366677297979943348866069441526047857),
                fe(195301262267610361172900534545341678525),
                fe(2123819604855435621395010720102555908),
                fe(96986567016099155020743003059932893278),
                fe(248057324456138589201107100302767574618),
                fe(198550227406618432920989444844179399959),
                fe(177812676254201468976352471992022853250),
                fe(211374136170376198628213577084029234846),
                fe(105785712445518775732830634260671010540),
                fe(122179368175793934687780753063673096166),
                fe(126848216361173160497844444214866193172),
                fe(22264167580742653700039698161547403113),
                fe(234275908658634858929918842923795514466),
                fe(189409811294589697028796856023159619258),
                fe(75017033107075630953974011872571911999),
                fe(144945344860351075586575129489570116296),
                fe(261991152616933455169437121254310265934),
                fe(18450316039330448878816627264054416127),
            ],
        }
    }

    fn apply_sbox(&self, state: &mut [FieldElement; 2], exponent: u128) {
        for value in state.iter_mut().take(self.m) {
            *value = value.pow(exponent);
        }
    }

    fn apply_mds(&self, state: &[FieldElement; 2]) -> [FieldElement; 2] {
        let mut mixed = [FieldElement::zero(); 2];
        for (row_index, row) in self.mds.iter().enumerate().take(self.m) {
            mixed[row_index] = row
                .iter()
                .zip(state.iter())
                .take(self.m)
                .fold(FieldElement::zero(), |acc, (&coefficient, &value)| {
                    acc + coefficient * value
                });
        }
        mixed
    }

    fn add_round_constants(&self, state: &mut [FieldElement; 2], offset: usize) {
        for (index, value) in state.iter_mut().enumerate().take(self.m) {
            *value = *value + self.round_constants[offset + index];
        }
    }

    fn apply_round(&self, state: &mut [FieldElement; 2], round: usize) {
        self.apply_sbox(state, self.alpha);
        *state = self.apply_mds(state);
        self.add_round_constants(state, 2 * round * self.m);

        self.apply_sbox(state, self.alphainv);
        *state = self.apply_mds(state);
        self.add_round_constants(state, 2 * round * self.m + self.m);
    }

    /// Rescue-Prime hash function.
    pub fn hash(&self, input_element: FieldElement) -> FieldElement {
        let mut state = [input_element, FieldElement::zero()];

        for round in 0..self.n {
            self.apply_round(&mut state, round);
        }

        state[0]
    }

    /// Compute the algebraic execution trace.
    pub fn trace(&self, input_element: FieldElement) -> Vec<Vec<FieldElement>> {
        let mut trace = Vec::with_capacity(self.n + 1);
        let mut state = [input_element, FieldElement::zero()];
        trace.push(state.to_vec());

        for round in 0..self.n {
            self.apply_round(&mut state, round);
            trace.push(state.to_vec());
        }

        trace
    }

    /// Boundary constraints: [(cycle, register, value), ...]
    pub fn boundary_constraints(
        &self,
        output_element: FieldElement,
    ) -> Vec<(usize, usize, FieldElement)> {
        vec![
            (0, 1, FieldElement::zero()), // capacity starts at zero
            (self.n, 0, output_element),  // rate part is the output
        ]
    }

    /// Interpolate round constants as multivariate polynomials in the cycle variable.
    pub fn round_constants_polynomials(
        &self,
        omicron: FieldElement,
    ) -> (Vec<MPolynomial>, Vec<MPolynomial>) {
        let domain: Vec<FieldElement> = (0..self.n)
            .map(|round| omicron.pow(round as u128))
            .collect();
        let mut first_step_constants = Vec::new();
        for i in 0..self.m {
            let values: Vec<FieldElement> = (0..self.n)
                .map(|r| self.round_constants[2 * r * self.m + i])
                .collect();
            let univariate = Polynomial::interpolate_domain(&domain, &values);
            let multivariate = MPolynomial::lift(&univariate, 0);
            first_step_constants.push(multivariate);
        }

        let mut second_step_constants = Vec::new();
        for i in 0..self.m {
            let values: Vec<FieldElement> = (0..self.n)
                .map(|r| self.round_constants[2 * r * self.m + self.m + i])
                .collect();
            let univariate = Polynomial::interpolate_domain(&domain, &values);
            let multivariate = MPolynomial::lift(&univariate, 0);
            second_step_constants.push(multivariate);
        }

        (first_step_constants, second_step_constants)
    }

    /// Transition constraints as multivariate polynomials (AIR).
    pub fn transition_constraints(&self, omicron: FieldElement) -> Vec<MPolynomial> {
        let (first_step_constants, second_step_constants) =
            self.round_constants_polynomials(omicron);

        // Variables: [cycle_index, prev_state_0, prev_state_1, next_state_0, next_state_1]
        let variables = MPolynomial::variables(1 + 2 * self.m);
        let previous_state = &variables[1..1 + self.m];
        let next_state = &variables[1 + self.m..1 + 2 * self.m];

        let mut air = Vec::new();
        for (i, first_step_constant) in first_step_constants.iter().enumerate().take(self.m) {
            // LHS: sum(MDS[i][k] * prev_state[k]^alpha) + first_step_constants[i]
            let mut lhs = MPolynomial::constant(FieldElement::zero());
            for (k, previous_value) in previous_state.iter().enumerate().take(self.m) {
                lhs = lhs
                    + MPolynomial::constant(self.mds[i][k])
                        * previous_value.clone().pow(self.alpha as usize);
            }
            lhs = lhs + first_step_constant.clone();

            // RHS: (sum(MDSinv[i][k] * (next_state[k] - second_step_constants[k])))^alpha
            let mut rhs = MPolynomial::constant(FieldElement::zero());
            for (k, next_value) in next_state.iter().enumerate().take(self.m) {
                rhs = rhs
                    + MPolynomial::constant(self.mds_inv[i][k])
                        * (next_value.clone() - second_step_constants[k].clone());
            }
            rhs = rhs.pow(self.alpha as usize);

            air.push(lhs - rhs);
        }

        air
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rescue_prime_hash_vector_1() {
        let rp = RescuePrime::new();
        let result = rp.hash(FieldElement::new(1));
        assert_eq!(
            result,
            FieldElement::new(244180265933090377212304188905974087294),
            "rescue prime test vector 1 failed"
        );
    }

    #[test]
    fn test_rescue_prime_hash_vector_2() {
        let rp = RescuePrime::new();
        let result = rp.hash(FieldElement::new(57322816861100832358702415967512842988));
        assert_eq!(
            result,
            FieldElement::new(89633745865384635541695204788332415101),
            "rescue prime test vector 2 failed"
        );
    }

    #[test]
    fn test_rescue_prime_trace_boundary() {
        let rp = RescuePrime::new();
        let a = FieldElement::new(57322816861100832358702415967512842988);
        let b = FieldElement::new(89633745865384635541695204788332415101);
        let trace = rp.trace(a);
        assert_eq!(trace[0][0], a);
        assert_eq!(trace.last().unwrap()[0], b);
    }
}
