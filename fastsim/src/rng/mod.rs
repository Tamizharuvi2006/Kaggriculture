//! Exact CPython 3.12 `_randommodule.c` MT19937 random generator.

const N: usize = 624;
const M: usize = 397;
const MATRIX_A: u32 = 0x9908b0df;
const UPPER_MASK: u32 = 0x80000000;
const LOWER_MASK: u32 = 0x7fffffff;

#[derive(Clone, Debug)]
pub struct PythonRng {
    state: [u32; N],
    index: usize,
}

impl PythonRng {
    pub fn new(seed: u64) -> Self {
        let mut rng = Self {
            state: [0; N],
            index: N + 1,
        };
        rng.seed(seed);
        rng
    }

    fn init_genrand(&mut self, s: u32) {
        self.state[0] = s;
        for mti in 1..N {
            self.state[mti] = (1812433253u32)
                .wrapping_mul(self.state[mti - 1] ^ (self.state[mti - 1] >> 30))
                .wrapping_add(mti as u32);
        }
        self.index = N;
    }

    fn init_by_array(&mut self, init_key: &[u32]) {
        self.init_genrand(19650218);
        let mut i = 1usize;
        let mut j = 0usize;
        let mut k = if N > init_key.len() { N } else { init_key.len() };

        while k > 0 {
            self.state[i] = (self.state[i]
                ^ ((self.state[i - 1] ^ (self.state[i - 1] >> 30)).wrapping_mul(1664525)))
                .wrapping_add(init_key[j])
                .wrapping_add(j as u32);
            i += 1;
            j += 1;
            if i >= N {
                self.state[0] = self.state[N - 1];
                i = 1;
            }
            if j >= init_key.len() {
                j = 0;
            }
            k -= 1;
        }

        k = N - 1;
        while k > 0 {
            self.state[i] = (self.state[i]
                ^ ((self.state[i - 1] ^ (self.state[i - 1] >> 30)).wrapping_mul(1566083941)))
                .wrapping_sub(i as u32);
            i += 1;
            if i >= N {
                self.state[0] = self.state[N - 1];
                i = 1;
            }
            k -= 1;
        }

        self.state[0] = 0x80000000;
        self.index = N;
    }

    pub fn seed(&mut self, seed: u64) {
        // CPython converts positive int into array of 32-bit words (little-endian)
        let mut key = Vec::new();
        let mut rem = seed;
        while rem > 0 {
            key.push((rem & 0xFFFFFFFF) as u32);
            rem >>= 32;
        }
        if key.is_empty() {
            key.push(0);
        }
        self.init_by_array(&key);
    }

    pub fn genrand_int32(&mut self) -> u32 {
        let mag01 = [0u32, MATRIX_A];
        if self.index >= N {
            if self.index == N + 1 {
                self.init_genrand(5489);
            }
            for kk in 0..(N - M) {
                let y = (self.state[kk] & UPPER_MASK) | (self.state[kk + 1] & LOWER_MASK);
                self.state[kk] = self.state[kk + M] ^ (y >> 1) ^ mag01[(y & 1) as usize];
            }
            for kk in (N - M)..(N - 1) {
                let y = (self.state[kk] & UPPER_MASK) | (self.state[kk + 1] & LOWER_MASK);
                self.state[kk] = self.state[kk + M - N] ^ (y >> 1) ^ mag01[(y & 1) as usize];
            }
            let y = (self.state[N - 1] & UPPER_MASK) | (self.state[0] & LOWER_MASK);
            self.state[N - 1] = self.state[M - 1] ^ (y >> 1) ^ mag01[(y & 1) as usize];
            self.index = 0;
        }

        let mut y = self.state[self.index];
        self.index += 1;

        y ^= y >> 11;
        y ^= (y << 7) & 0x9d2c5680;
        y ^= (y << 15) & 0xefc60000;
        y ^= y >> 18;

        y
    }

    pub fn random(&mut self) -> f64 {
        let a = (self.genrand_int32() >> 5) as f64;
        let b = (self.genrand_int32() >> 6) as f64;
        (a * 67108864.0 + b) * (1.0 / 9007199254740992.0)
    }

    pub fn getrandbits(&mut self, k: usize) -> u32 {
        if k == 0 { return 0; }
        if k <= 32 {
            let val = self.genrand_int32();
            val >> (32 - k)
        } else {
            self.genrand_int32()
        }
    }

    pub fn choice<T: Clone>(&mut self, items: &[T]) -> T {
        assert!(!items.is_empty(), "Cannot choice from empty slice");
        let n = items.len();
        let k = (32 - (n as u32).leading_zeros()) as usize;
        let mut r = self.getrandbits(k) as usize;
        while r >= n {
            r = self.getrandbits(k) as usize;
        }
        items[r].clone()
    }
}
