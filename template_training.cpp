/*
 * Copyright (c) 2019, ETH Zurich
 */

#include <cassert>
#include <iostream>
#include <vector>
#include <array>
#include <cmath>
#include <chrono>
#include <thread>
#include <algorithm>

#include <omp.h>

// problem configuration
constexpr int X = {{X}}; 
constexpr int Y = {{Y}}; 
constexpr int Z = {{Z}}; 
constexpr int HX = {{HX}}; 
constexpr int HY = {{HY}}; 
constexpr int HZ = {{HZ}}; 
constexpr int NX = {{TILING.NX}}; 
constexpr int NY = {{TILING.NY}}; 
constexpr int NZ = {{TILING.NZ}}; 

// implement infrastructure
template<typename T>
class directory {
public:
    directory() {}
    directory(T value) { _mem.fill(value); }

    T& operator()(int i, int j, int k) { 
        return _mem[(i + 1) + 3 * (j + 1) + 9 * (k + 1)]; 
    }
    const T operator()(int i, int j, int k) const { 
        return _mem[(i + 1) + 3 * (j + 1) + 9 * (k + 1)]; 
    }
private:
    std::array<T, 27> _mem; 
};

template<typename T, int VX, int VY, int VZ>
class array_view {
public:
    array_view(T* mem) : _mem(mem) {}

    T& operator()(int i, int j, int k) { 
        return _mem[i + j * (VX + 2*HX) + k * (VX + 2*HX) * (VY + 2*HY)]; 
    }
    const T& operator()(int i, int j, int k) const { 
        return _mem[i + j * (VX + 2*HX) + k * (VX + 2*HX) * (VY + 2*HY)]; 
    }
private:
    T* _mem;
};

template<typename T, int VX, int VY, int VZ>
class array {
public:
    array() : _mem((VX + 2*HX) * (VY + 2*HY) * (VZ + 2*HZ)) { 
        std::generate(std::begin(_mem), std::end(_mem), std::rand); 
    }
    array(T value) : _mem((VX + 2*HX) * (VY + 2*HY) * (VZ + 2*HZ)) { 
        std::generate(std::begin(_mem), std::end(_mem), [=]() { return value; }); 
    }

    T& operator()(int i, int j, int k) { 
        return _mem[i + j * (VX + 2*HX) + k * (VX + 2*HX) * (VY + 2*HY)]; 
    }
    const T& operator()(int i, int j, int k) const { 
        return _mem[i + j * (VX + 2*HX) + k * (VX + 2*HX) * (VY + 2*HY)]; 
    }

    size_t size() const { return _mem.size(); }
private:
    std::vector<T> _mem;
};

template<typename T, int VX, int VY, int VZ>
class stack_array {
public:
    T& operator()(int i, int j, int k) { 
        return _mem[i + j * (VX + 2*HX) + k * (VX + 2*HX) * (VY + 2*HY)]; 
    }
    const T& operator()(int i, int j, int k) const { 
        return _mem[i + j * (VX + 2*HX) + k * (VX + 2*HX) * (VY + 2*HY)]; 
    }

    size_t size() const { return _mem.size(); }
private:
    std::array<T, (VX + 2*HX) * (VY + 2*HY) * (VZ + 2*HZ)> _mem;
};

// define the array types
typedef array<double, X, Y, Z> array_3d;
typedef array_view<double, X, Y, Z> array_view_3d;

// store rectangular range
struct loop_info {
    int ibeg; int iend;
    int jbeg; int jend;
    int kbeg; int kend;
};

// logging helpers
void print() { 
    std::cout << std::endl;
}
template<typename T, typename... TArgs>
void print(const T& val, TArgs&&... args) {
    std::cout << val;
    print(args...);
}
template<typename T, typename... TArgs>
void log(const T& val, TArgs&&... args) {
    print(val, args...);
}
// timing helpers
template<typename... TArgs>
auto start_timers(TArgs&... args) -> decltype(std::chrono::high_resolution_clock::now()) {
    (void) std::initializer_list<int>{(args = 0.0, 0)...};
    return std::chrono::high_resolution_clock::now();
}
template<typename T, typename... TArgs>
auto update_timers(T& start, TArgs&... args) 
    -> decltype(std::chrono::high_resolution_clock::now()) {
    auto stop = std::chrono::high_resolution_clock::now();
    double diff = std::chrono::duration<double, std::milli>(stop - start).count();
    (void) std::initializer_list<int>{(args += diff, 0)...};
    return stop;
}

// apply periodic boundary condition
template<typename TArray>
void make_periodic(TArray& data) {
    // mirror the i dimension
    for(int k = 0; k < Z + 2 * HZ; ++k)
        for(int j = 0; j < Y + 2 * HY; ++j)
            for(int i = 0; i < HX; ++i) {       
                data(i,j,k) = data(i+X,j,k);
                data(i+X+HX,j,k) = data(i+HX,j,k);
            }
    // mirror the j dimension
    for(int k = 0; k < Z + 2 * HZ; ++k)
        for(int j = 0; j < HY; ++j)
            for(int i = 0; i < X + 2 * HX; ++i) {       
                data(i,j,k) = data(i,j+Y,k);
                data(i,j+Y+HY,k) = data(i,j+HY,k);
            }
    // mirror the k dimension
    for(int k = 0; k < HZ; ++k)
        for(int j = 0; j < Y + 2 * HY; ++j)
            for(int i = 0; i < X + 2 * HX; ++i) {       
                data(i,j,k) = data(i,j,k+Z);
                data(i,j,k+Z+HZ) = data(i,j,k+HZ);
            }
}

int main(int argc, char **argv) {
    // print the configuration
    log("-> configuration");
    log("   - variant {{VARIANT}}");
    log("   - domain {{X}}, {{Y}}, {{Z}}");
    log("   - runs {{RUNS}}");
    log("   - verify {{VERIFY}}");
    log("   - threads ", omp_get_max_threads());
    
    // compute subdomain size and offset
    constexpr int SX = (X + NX - 1) / NX; 
    constexpr int SY = (Y + NY - 1) / NY; 
    constexpr int SZ = (Z + NZ - 1) / NZ; 
    constexpr int OX = -(SX * NX - X) / 2; 
    constexpr int OY = -(SY * NY - Y) / 2; 
    constexpr int OZ = -(SZ * NZ - Z) / 2; 
   
    // compute index range
    int index[] = { 0, 0, 0 };
    int xbeg = std::min(std::max(HX + OX + index[0] * SX, HX), X + HX);   
    int ybeg = std::min(std::max(HY + OY + index[1] * SY, HY), Y + HY); 
    int zbeg = std::min(std::max(HZ + OZ + index[2] * SZ, HZ), Z + HZ); 
    int xend = std::min(std::max(HX + OX + (index[0] + 1) * SX, HX), X + HX);  
    int yend = std::min(std::max(HY + OY + (index[1] + 1) * SY, HY), Y + HY);  
    int zend = std::min(std::max(HZ + OZ + (index[2] + 1) * SZ, HZ), Z + HZ);  

    typedef array<double, SX, SY, SZ> sarray_3d;
    typedef array_view<double, SX, SY, SZ> sarray_view_3d;

    // allocate the input and output arrays and views of the rank local data
    std::srand(0); {% for input in TILING.INPUTS %}
    array_3d _{{input}}; {% endfor %}{% for output in TILING.OUTPUTS %}
    array_3d _{{output}}(0.0); {% endfor %}{% for temp in TILING.TEMPS %}
    sarray_3d _{{temp}}(0.0); {% endfor %}{% for group0 in TILING.GROUPS %}{% for temp in group0.TEMPS %}
    sarray_3d _{{temp}}(0.0); {% endfor %}{% for group1 in group0.GROUPS %}{% for temp in group1.TEMPS %}
    sarray_3d _{{temp}}(0.0); {% endfor %}{% endfor %}{% endfor %}{% for input in TILING.INPUTS %}
    array_view_3d __{{input}}(&(_{{input}}(xbeg, ybeg, zbeg))); {% endfor %}{% for output in TILING.OUTPUTS %}
    array_view_3d __{{output}}(&(_{{output}}(xbeg, ybeg, zbeg))); {% endfor %}{% for temp in TILING.TEMPS %}
    sarray_view_3d __{{temp}}(&(_{{temp}}(HX, HY, HZ))); {% endfor %}{% for group0 in TILING.GROUPS %}{% for temp in group0.TEMPS %}
    sarray_view_3d __{{temp}}(&(_{{temp}}(HX, HY, HZ))); {% endfor %}{% for group1 in group0.GROUPS %}{% for temp in group1.TEMPS %}
    sarray_view_3d __{{temp}}(&(_{{temp}}(HX, HY, HZ))); {% endfor %}{% endfor %}{% endfor %}
    {% for input in TILING.INPUTS %}
    make_periodic(_{{input}}); {% endfor %}
    
    log("-> preparing loops..."); {% for group0 in TILING.GROUPS if group0.LOOPS %}{% for group1 in group0.GROUPS if group1.LOOPS %}
    std::vector<loop_info> _tiles_group{{group1.ID}}; {% endfor %}{% endfor %}{% for group0 in TILING.GROUPS if group0.LOOPS %}{% for group1 in group0.GROUPS if group1.LOOPS %}{% for name, bounds in group1.LOOPS.items() %}
    std::vector<loop_info> _loops_{{name}}; {% endfor %}{% endfor %}{% endfor %}
    {% for group0 in TILING.GROUPS if group0.LOOPS %}{% for group1 in group0.GROUPS if group1.LOOPS %}
    // compute group{{group1.ID}} tile size
    constexpr int TX{{group1.ID}} = (SX + {{group1.NX}} - 1) / {{group1.NX}};
    constexpr int TY{{group1.ID}} = (SY + {{group1.NY}} - 1) / {{group1.NY}};
    constexpr int TZ{{group1.ID}} = (SZ + {{group1.NZ}} - 1) / {{group1.NZ}};
    constexpr int OX{{group1.ID}} = -(TX{{group1.ID}} * {{group1.NX}} - SX) / 2;
    constexpr int OY{{group1.ID}} = -(TY{{group1.ID}} * {{group1.NY}} - SY) / 2;
    constexpr int OZ{{group1.ID}} = -(TZ{{group1.ID}} * {{group1.NZ}} - SZ) / 2;

    // define group{{group1.ID}} array types
    typedef stack_array<double, TX{{group1.ID}}, TY{{group1.ID}}, TZ{{group1.ID}}> tarray{{group1.ID}}_3d;
    typedef array_view<double, TX{{group1.ID}}, TY{{group1.ID}}, TZ{{group1.ID}}> tarray{{group1.ID}}_view_3d;
 
    // compute group{{group1.ID}} tile loops and offsets
    for(int z = 0; z < {{group1.NZ}}; ++z)
        for(int y = 0; y < {{group1.NY}}; ++y)
            for(int x = 0; x < {{group1.NX}}; ++x) { 
                loop_info tile = {
                    x * TX{{group1.ID}} + OX{{group1.ID}}, (x + 1) * TX{{group1.ID}} + OX{{group1.ID}},
                    y * TY{{group1.ID}} + OY{{group1.ID}}, (y + 1) * TY{{group1.ID}} + OY{{group1.ID}},
                    z * TZ{{group1.ID}} + OZ{{group1.ID}}, (z + 1) * TZ{{group1.ID}} + OZ{{group1.ID}}
                };
                _tiles_group{{group1.ID}}.push_back(tile);
                {% for name, bounds1 in group1.LOOPS.items() %}{% set bounds0 = group0.LOOPS[name] %}
                // compute loop boundary of inner tiles
                loop_info loop_{{name}} = {
                    tile.ibeg + {{bounds1[0][0]}}, tile.iend + {{bounds1[0][1]}},
                    tile.jbeg + {{bounds1[1][0]}}, tile.jend + {{bounds1[1][1]}},
                    tile.kbeg + {{bounds1[2][0]}}, tile.kend + {{bounds1[2][1]}}
                };

                // extend boundaries of outer tiles
                if(x == 0) loop_{{name}}.ibeg = std::min(loop_{{name}}.ibeg, {{bounds0[0][0]}});  
                if(y == 0) loop_{{name}}.jbeg = std::min(loop_{{name}}.jbeg, {{bounds0[1][0]}});  
                if(z == 0) loop_{{name}}.kbeg = std::min(loop_{{name}}.kbeg, {{bounds0[2][0]}});  
                if(x == {{group1.NX}} - 1) loop_{{name}}.iend = std::max(loop_{{name}}.iend, xend - xbeg + {{bounds0[0][1]}});  
                if(y == {{group1.NY}} - 1) loop_{{name}}.jend = std::max(loop_{{name}}.jend, yend - ybeg + {{bounds0[1][1]}});  
                if(z == {{group1.NZ}} - 1) loop_{{name}}.kend = std::max(loop_{{name}}.kend, zend - zbeg + {{bounds0[2][1]}});  
                
                // subtract the tile offset
                loop_{{name}}.ibeg -= tile.ibeg; 
                loop_{{name}}.iend -= tile.ibeg;
                loop_{{name}}.jbeg -= tile.jbeg; 
                loop_{{name}}.jend -= tile.jbeg;
                loop_{{name}}.kbeg -= tile.kbeg; 
                loop_{{name}}.kend -= tile.kbeg;
                
                _loops_{{name}}.push_back(loop_{{name}}); 
                {% endfor %}
            }{% endfor %}{% endfor %}

    // define timing variables
    double total_time;
    for(int run = 0; run < 2 * {{RUNS}}; ++run) {
        {% if FLUSH %}
        // flush the cache
        log("-> flushing the caches..."); 
        std::vector<double> cache(1000000);
        double acc = 0.0;
        #pragma omp parallel for
        for(int i=0; i<1000000; ++i) cache[i] = 0;
        #pragma omp parallel for reduction(+:acc)
        for(int i=0; i<1000000; ++i) acc += cache[i];
        log("    - and the sum is ", acc); 
        {% endif %}
        // run the distributed stencil program    
        log("-> computing distributed..."); 
        auto clock = start_timers(total_time);
        {% for entry in SCHEDULE %}{% if entry.TYPE == "COMP" %}{% for group1 in entry.GROUP.GROUPS %}
        #pragma omp parallel for schedule(static, 1)
        for(int idx = 0; idx < {{group1.NX}} * {{group1.NY}} * {{group1.NZ}}; idx += 20) { 
            // initialize array views
            loop_info tile = _tiles_group{{group1.ID}}[idx]; 
            {% for input in group1.INPUTS %}{% if input in TILING.INPUTS %}
            array_view_3d {{input}}(&__{{input}}(tile.ibeg, tile.jbeg, tile.kbeg)); {% else %}
            sarray_view_3d {{input}}(&__{{input}}(tile.ibeg, tile.jbeg, tile.kbeg)); {% endif %}{% endfor %}{% for output in group1.OUTPUTS %}{% if output in TILING.OUTPUTS %}
            array_view_3d {{output}}(&__{{output}}(tile.ibeg, tile.jbeg, tile.kbeg)); {% else %}
            sarray_view_3d {{output}}(&__{{output}}(tile.ibeg, tile.jbeg, tile.kbeg)); {% endif %}{% endfor %}
            {% for temp in group1.TEMPS %}
            tarray{{group1.ID}}_3d ___{{temp}}; {% endfor %}{% for temp in group1.TEMPS %}
            tarray{{group1.ID}}_view_3d {{temp}}(&___{{temp}}(HX, HY, HZ)); {% endfor %}
            {% for stencil in group1.STENCILS %}
            {
                // apply {{stencil.NAME}} stencil
                int ibeg = _loops_{{stencil.NAME}}[idx].ibeg;
                int iend = _loops_{{stencil.NAME}}[idx].iend;
                int jbeg = _loops_{{stencil.NAME}}[idx].jbeg;
                int jend = _loops_{{stencil.NAME}}[idx].jend;
                int kbeg = _loops_{{stencil.NAME}}[idx].kbeg;
                int kend = _loops_{{stencil.NAME}}[idx].kend;
                for(int k = kbeg; k < kend; ++k)
                    for(int j = jbeg; j < jend; ++j)
                        #pragma omp simd
                        for(int i = ibeg; i < iend; ++i) {
                            assert(i >= -HX && i < TX{{group1.ID}} + HX);
                            assert(j >= -HY && j < TY{{group1.ID}} + HY);
                            assert(k >= -HZ && k < TZ{{group1.ID}} + HZ);

                            {{stencil.LAMBDA}}
                            {{stencil.NAME}}(i, j, k) = res;           
                        } 
            }{% endfor %}
        }{% endfor %}{% endif %}{% endfor %}
        clock = update_timers(clock, total_time); 
        
        // time every forth iteration and wait
        if(run % 2 == 1) {
            log("   - total time (min/median/max) [ms]: ", total_time);
            log("   - halo time (min/median/max) [ms]: ",  0);
            // wait for 100 ms
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    } 
}
