#include "rolling_mean.hpp"

#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

int main() {
    const std::vector<double> input{1.0, 2.0, 3.0, 4.0};
    const auto output = v4_native::rolling_mean(input, 2);
    require(output.size() == 3, "wrong output length");
    require(std::abs(output[0] - 1.5) < 1e-12, "wrong first mean");
    require(std::abs(output[1] - 2.5) < 1e-12, "wrong second mean");
    require(std::abs(output[2] - 3.5) < 1e-12, "wrong third mean");
    require(input[0] == 1.0 && input[3] == 4.0, "input was modified");
    require(v4_native::rolling_mean(input, 5).empty(), "oversized window must be empty");
    require(v4_native::rolling_mean({}, 1).empty(), "empty input must be empty");
    const auto large = v4_native::rolling_mean({1e308, 1e308}, 2);
    require(large.size() == 1 && std::isfinite(large[0]) && large[0] == 1e308,
            "large finite values must retain a finite mean");

    bool rejected_window = false;
    try {
        (void)v4_native::rolling_mean(input, 0);
    } catch (const std::invalid_argument&) {
        rejected_window = true;
    }
    require(rejected_window, "zero window was accepted");

    bool rejected_nonfinite = false;
    try {
        (void)v4_native::rolling_mean({1.0, std::numeric_limits<double>::quiet_NaN()}, 2);
    } catch (const std::invalid_argument&) {
        rejected_nonfinite = true;
    }
    require(rejected_nonfinite, "non-finite input was accepted");
}
