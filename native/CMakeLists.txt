cmake_minimum_required(VERSION 3.16)
project(v4_native_probe LANGUAGES CXX)

add_library(rolling_mean STATIC rolling_mean.cpp)
target_compile_features(rolling_mean PUBLIC cxx_std_17)
target_include_directories(rolling_mean PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

add_executable(rolling_mean_test rolling_mean_test.cpp)
target_link_libraries(rolling_mean_test PRIVATE rolling_mean)

enable_testing()
add_test(NAME rolling_mean_test COMMAND rolling_mean_test)
