#include "rolling_mean.hpp"

#include <algorithm>
#include <cstddef>
#include <exception>
#include <vector>

#ifdef _WIN32
#define V5_EXPORT __declspec(dllexport)
#else
#define V5_EXPORT __attribute__((visibility("default")))
#endif

extern "C" V5_EXPORT int v5_rolling_mean(const double* input, std::size_t count,
                                           std::size_t window, double* output,
                                           std::size_t output_capacity) noexcept {
    if ((!input && count) || (!output && output_capacity) || window == 0 ||
        output_capacity != (window <= count ? count - window + 1 : 0)) {
        return 1;
    }
    try {
        std::vector<double> values;
        if (count) {
            values.assign(input, input + count);
        }
        const std::vector<double> means = v4_native::rolling_mean(values, window);
        if (!means.empty()) {
            std::copy(means.begin(), means.end(), output);
        }
        return 0;
    } catch (const std::exception&) {
        return 2;
    } catch (...) {
        return 3;
    }
}
