#include "rolling_mean.hpp"

#include <cmath>
#include <stdexcept>

namespace v4_native {

std::vector<double> rolling_mean(const std::vector<double>& values, std::size_t window) {
    if (window == 0) {
        throw std::invalid_argument("window must be positive");
    }
    for (double value : values) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument("values must be finite");
        }
    }
    if (window > values.size()) {
        return {};
    }

    std::vector<double> result;
    result.reserve(values.size() - window + 1);
    double sum = 0.0;
    const double divisor = static_cast<double>(window);
    for (std::size_t i = 0; i < values.size(); ++i) {
        sum += values[i] / divisor;
        if (i >= window) {
            sum -= values[i - window] / divisor;
        }
        if (i >= window - 1) {
            result.push_back(sum);
        }
    }
    return result;
}

}  // namespace v4_native
