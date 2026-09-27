#include "rolling_mean.hpp"

#include <exception>
#include <iomanip>
#include <iostream>
#include <vector>

int main() {
    try {
        std::size_t window = 0;
        if (!(std::cin >> window)) {
            return 2;
        }
        std::vector<double> values;
        double value = 0.0;
        while (std::cin >> value) {
            values.push_back(value);
        }
        if (!std::cin.eof()) {
            return 2;
        }
        std::cout << std::setprecision(17);
        for (double mean : v4_native::rolling_mean(values, window)) {
            std::cout << mean << '\n';
        }
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
