#pragma once

#include <cstddef>
#include <vector>

namespace v4_native {

// Full windows in input order. This standalone probe does not replace the Python tool.
std::vector<double> rolling_mean(const std::vector<double>& values, std::size_t window);

}  // namespace v4_native
