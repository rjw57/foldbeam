#include "constants.h"
#include "pj_mlfn.h"

const float TMERC_EPS10 = 1.e-10f;

const float TMERC_FC1 = 1.f;
const float TMERC_FC2 = .5f;
const float TMERC_FC3 = .16666666666666666666f;
const float TMERC_FC4 = .08333333333333333333f;
const float TMERC_FC5 = .05f;
const float TMERC_FC6 = .03333333333333333333f;
const float TMERC_FC7 = .02380952380952380952f;
const float TMERC_FC8 = .01785714285714285714f;

/* ellipsoid */
float2 tmerc_e_forward(float2 lp, float k0, float es, float esp, float en[5], float ml0, int* err)
{
    float2 xy;
    float al, als, n, cosphi, sinphi, t;

    /*
     * Fail if our longitude is more than 90 degrees from the 
     * central meridian since the results are essentially garbage. 
     * Is error -20 really an appropriate return value?
     * 
     *  http://trac.osgeo.org/proj/ticket/5
     */
    if( lp.x < -HALFPI || lp.x > HALFPI )
    {
        xy.x = HUGE_VAL;
        xy.y = HUGE_VAL;
        *err = -14;
        return xy;
    }

    sinphi = sin(lp.y); cosphi = cos(lp.y);
    t = fabs(cosphi) > 1e-10f ? sinphi/cosphi : 0.f;
    t *= t;
    al = cosphi * lp.x;
    als = al * al;
    al /= sqrt(1.f - es * sinphi * sinphi);
    n = esp * cosphi * cosphi;
    xy.x = k0 * al * (TMERC_FC1 +
            TMERC_FC3 * als * (1.f - t + n +
            TMERC_FC5 * als * (5.f + t * (t - 18.f) + n * (14.f - 58.f * t)
            + TMERC_FC7 * als * (61.f + t * ( t * (179.f - t) - 479.f ) )
            )));
    xy.y = k0 * (pj_mlfn(lp.y, sinphi, cosphi, en) - ml0 +
            sinphi * al * lp.x * TMERC_FC2 * ( 1.f +
            TMERC_FC4 * als * (5.f - t + n * (9.f + 4.f * n) +
            TMERC_FC6 * als * (61.f + t * (t - 58.f) + n * (270.f - 330 * t)
            + TMERC_FC8 * als * (1385.f + t * ( t * (543.f - t) - 3111.f) )
            ))));
    return (xy);
}


float2 tmerc_s_forward(float2 xy, float phi0, float esp, float ml0, int* err)
{
    /* sphere */
    float2 lp;
    float b, cosphi;

    /*
     * Fail if our longitude is more than 90 degrees from the 
     * central meridian since the results are essentially garbage. 
     * Is error -20 really an appropriate return value?
     * 
     *  http://trac.osgeo.org/proj/ticket/5
     */
    if( lp.x < -HALFPI || lp.x > HALFPI )
    {
        xy.x = HUGE_VAL;
        xy.y = HUGE_VAL;
        *err = -14;
        return xy;
    }

    b = (cosphi = cos(lp.y)) * sin(lp.x);
    if (fabs(fabs(b) - 1.f) <= TMERC_EPS10)
    {
        *err = -1;
        return xy;
    }
    xy.x = ml0 * log((1.f + b) / (1.f - b));
    if ((b = fabs( xy.y = cosphi * cos(lp.x) / sqrt(1.f - b * b) )) >= 1.f) {
        if ((b - 1.f) > TMERC_EPS10)
        {
            *err = -1;
            return xy;
        }
        else xy.y = 0.f;
    } else
        xy.y = acos(xy.y);
    if (lp.y < 0.f) xy.y = -xy.y;
    xy.y = esp * (xy.y - phi0);
    return (xy);
}
#if 0
INVERSE(e_inverse); /* ellipsoid */
	double n, con, cosphi, d, ds, sinphi, t;

	lp.y = pj_inv_mlfn(P->ctx, P->ml0 + xy.y / P->k0, P->es, P->en);
	if (fabs(lp.y) >= HALFPI) {
		lp.y = xy.y < 0. ? -HALFPI : HALFPI;
		lp.x = 0.;
	} else {
		sinphi = sin(lp.y);
		cosphi = cos(lp.y);
		t = fabs(cosphi) > 1e-10 ? sinphi/cosphi : 0.;
		n = P->esp * cosphi * cosphi;
		d = xy.x * sqrt(con = 1. - P->es * sinphi * sinphi) / P->k0;
		con *= t;
		t *= t;
		ds = d * d;
		lp.y -= (con * ds / (1.-P->es)) * TMERC_FC2 * (1. -
			ds * TMERC_FC4 * (5. + t * (3. - 9. *  n) + n * (1. - 4 * n) -
			ds * TMERC_FC6 * (61. + t * (90. - 252. * n +
				45. * t) + 46. * n
		   - ds * TMERC_FC8 * (1385. + t * (3633. + t * (4095. + 1574. * t)) )
			)));
		lp.x = d*(TMERC_FC1 -
			ds*TMERC_FC3*( 1. + 2.*t + n -
			ds*TMERC_FC5*(5. + t*(28. + 24.*t + 8.*n) + 6.*n
		   - ds * TMERC_FC7 * (61. + t * (662. + t * (1320. + 720. * t)) )
		))) / cosphi;
	}
	return (lp);
}
INVERSE(s_inverse); /* sphere */
	double h, g;

	h = exp(xy.x / aks0);
	g = .5 * (h - 1. / h);
	h = cos(P->phi0 + xy.y / aks0);
	lp.y = asin(sqrt((1. - h * h) / (1. + g * g)));
	if (xy.y < 0.) lp.y = -lp.y;
	lp.x = (g || h) ? atan2(g, h) : 0.;
	return (lp);
}
FREEUP;
	if (P) {
		if (P->en)
			pj_dalloc(P->en);
		pj_dalloc(P);
	}
}
	static PJ *
setup(PJ *P) { /* general initialization */
	if (P->es) {
		if (!(P->en = pj_enfn(P->es)))
			E_ERROR_0;
		P->ml0 = pj_mlfn(P->phi0, sin(P->phi0), cos(P->phi0), P->en);
		P->esp = P->es / (1. - P->es);
		P->inv = e_inverse;
		P->fwd = e_forward;
	} else {
		aks0 = P->k0;
		aks5 = .5 * aks0;
		P->inv = s_inverse;
		P->fwd = s_forward;
	}
	return P;
}
ENTRY1(tmerc, en)
ENDENTRY(setup(P))
ENTRY1(utm, en)
	int zone;

	if (!P->es) E_ERROR(-34);
	P->y0 = pj_param(P->ctx, P->params, "bsouth").i ? 10000000. : 0.;
	P->x0 = 500000.;
	if (pj_param(P->ctx, P->params, "tzone").i) /* zone input ? */
		if ((zone = pj_param(P->ctx, P->params, "izone").i) > 0 && zone <= 60)
			--zone;
		else
			E_ERROR(-35)
	else /* nearest central meridian input */
		if ((zone = floor((adjlon(P->lam0) + PI) * 30. / PI)) < 0)
			zone = 0;
		else if (zone >= 60)
			zone = 59;
	P->lam0 = (zone + .5) * PI / 30. - PI;
	P->k0 = 0.9996;
	P->phi0 = 0.;
ENDENTRY(setup(P))

#endif

void tmerc_setup(float k0, float es, float phi0, float en[5], float* ml0, float* esp)
{
    /* general initialization */
    if (es != 0.f) {
        pj_enfn(es, en);
        *ml0 = pj_mlfn(phi0, sin(phi0), cos(phi0), en);
        *esp = es / (1.f - es);
    } else {
        *esp = k0;
        *ml0 = .5 * *esp;
    }
}

float2 tmerc_forward(float2 lp, float k0, float e, float es, float phi0, int* err)
{
    float en[5];
    float ml0, esp;

    tmerc_setup(k0, es, phi0, en, &ml0, &esp);

    if(es != 0.f) {
        return tmerc_e_forward(lp, k0, es, esp, en, ml0, err);
    } else {
        return tmerc_s_forward(lp, phi0, esp, ml0, err);
    }
}

float2 tmerc_inverse(float2 lp, float k0, float e, float es, float phi0, int* err)
{
    float en[5];
    float ml0, esp;

    tmerc_setup(k0, es, phi0, en, &ml0, &esp);

    if(es != 0.f) {
        //return tmerc_e_inverse(lp, k0, es, esp, en, ml0, err);
    } else {
        //return tmerc_s_inverse(lp, phi0, esp, ml0, err);
    }
    return (float2)(0.f,0.f);
}

#ifdef USE_KERNEL
/* BEGIN_ENTRY: tmerc
 * KERNELS: tmerc_forward_kernel, tmerc_inverse_kernel
 * STANDARD_PARAMS: k0, e, es, phi0
 * END_ENTRY
 */

__attribute__((vec_type_hint(float2)))
__kernel void tmerc_forward_kernel(
        __global float2* in_lps, __global float2* out_xys, __global int* errors,
        float k0, float e, float es, float phi0)
{
    size_t idx = get_global_id(0);
    if(idx >= get_global_size(0))
        return;

    int err = 0;
    out_xys[idx] = tmerc_forward(in_lps[idx], k0, e, es, phi0, &err);
    errors[idx] = err;
}

__attribute__((vec_type_hint(float2)))
__kernel void tmerc_inverse_kernel(
        __global float2* in_lps, __global float2* out_xys, __global int* errors,
        float k0, float e, float es, float phi0)
{
    size_t idx = get_global_id(0);
    if(idx >= get_global_size(0))
        return;

    int err = 0;
    //out_xys[idx] = tmerc_inverse(in_lps[idx], k0, e, es, phi0, &err);
    errors[idx] = err;
}
#endif /* USE_KERNEL */

/* vim:filetype=c
 */
