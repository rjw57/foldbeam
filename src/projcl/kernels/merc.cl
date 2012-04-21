#include "constants.h"
#include "pj_msfn.h"
#include "pj_phi2.h"
#include "pj_tsfn.h"

#define EPS10 1.e-10

/* ellipsoid */
float2 merc_e_forward(float2 lp, float k0, float e, int* err)
{
    float2 xy;
    if (fabs(fabs(lp.y) - HALFPI) <= EPS10)
    {
        *err = 1;
        return (xy);
    }
    xy.x = k0 * lp.x;
    xy.y = - k0 * log(pj_tsfn(lp.y, sin(lp.y), e));
    return (xy);
}

/* spheroid */
float2 merc_s_forward(float2 lp, float k0, int* err)
{
    float2 xy;
    if (fabs(fabs(lp.y) - HALFPI) <= EPS10)
    {
        *err = 1;
        return (xy);
    }
    xy.x = k0 * lp.x;
    xy.y = k0 * log(tan(FORTPI + .5 * lp.y));
    return (xy);
}

/* ellipsoid */
float2 merc_e_inverse(float2 xy, float k0, float e, int *err)
{
    float2 lp;
    if ((lp.y = pj_phi2(exp(- xy.y / k0), e, err)) == HUGE_VAL)
    {
        *err = 1;
        return (lp);
    }
    lp.x = xy.x / k0;
    return (lp);
}

/* spheroid */
float2 merc_s_inverse(float2 xy, float k0, int *err)
{
    float2 lp;
    *err = 0;
    lp.y = HALFPI - 2. * atan(exp(-xy.y / k0));
    lp.x = xy.x / k0;
    return (lp);
}

float2 merc_forward(float2 lp, float k0, float e, float es, int tlat_ts, float rlat_ts, int* err)
{
    float phits=0.0;
    if(tlat_ts)
    {
        phits = fabs(rlat_ts);
        if (phits >= HALFPI) {
            *err = -24;
            return (lp);
        }
    }

    if(es != 0.f) {
        /* ellipsoid */
        if(tlat_ts)
            k0 = pj_msfn(sin(phits), cos(phits), es);
        return merc_e_forward(lp, k0, e, err);
    } else {
        /* sphere */
        if(tlat_ts)
            k0 = cos(phits);
        return merc_s_forward(lp, k0, err);
    }
}

float2 merc_inverse(float2 lp, float k0, float e, float es, int tlat_ts, float rlat_ts, int* err)
{
    float phits=0.0;
    if(tlat_ts)
    {
        phits = fabs(rlat_ts);
        if (phits >= HALFPI) {
            *err = -24;
            return (lp);
        }
    }

    if(es != 0.f) {
        /* ellipsoid */
        if(tlat_ts)
            k0 = pj_msfn(sin(phits), cos(phits), es);
        return merc_e_inverse(lp, k0, e, err);
    } else {
        /* sphere */
        if(tlat_ts)
            k0 = cos(phits);
        return merc_s_inverse(lp, k0, err);
    }
}

#ifdef USE_KERNEL
__kernel void merc_forward_kernel(
        __global float2* in_lps, __global float2* out_xys, __global int* errors,
        float k0, float e, float es, int tlat_ts, float rlat_ts)
{
    size_t idx = get_global_id(0);
    if(idx >= get_global_size(0))
        return;

    int err = 0;
    out_xys[idx] = merc_forward(in_lps[idx], k0, e, es, tlat_ts, rlat_ts, &err);
    errors[idx] = err;
}

__kernel void merc_inverse_kernel(
        __global float2* in_xys, __global float2* out_lps, __global int* errors,
        float k0, float e, float es, int tlat_ts, float rlat_ts)
{
    size_t idx = get_global_id(0);
    if(idx >= get_global_size(0))
        return;

    int err = 0;
    out_lps[idx] = merc_inverse(in_xys[idx], k0, e, es, tlat_ts, rlat_ts, &err);
    errors[idx] = err;
}
#endif /* USE_KERNEL */

/* vim:filetype=c
 */
