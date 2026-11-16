#ifndef XDUCK_MOTOR_PROFILE_H
#define XDUCK_MOTOR_PROFILE_H
/* 124-only candidate: DM-J10422P-2EC V1.1 manual, FD data 4 Mbps.
 * Mapping defaults are NOT application torque/travel limits. Actual positive
 * register values are verified and adopted before control is permitted. */
#if H7DM_DM_J10422P
#define MOTOR_PROFILE_CAN_BR 8U
#define MOTOR_PROFILE_DATA_SEG1 11U
#define MOTOR_PROFILE_DATA_SEG2 3U
#define MOTOR_PROFILE_PMAX 12.566f
#define MOTOR_PROFILE_VMAX 20.0f
#define MOTOR_PROFILE_TMAX 500.0f
#define MOTOR_PROFILE_WORKING_VMAX 12.5663706f /* 120 rpm output shaft */
#define MOTOR_PROFILE_WORKING_TMAX 400.0f /* vendor peak, not continuous rating */
#define MOTOR_PROFILE_TIMEOUT_COUNTS_MAX 8000U /* 50 us/count = 400 ms */
#else
#define MOTOR_PROFILE_CAN_BR 3U
#define MOTOR_PROFILE_DATA_SEG1 9U
#define MOTOR_PROFILE_DATA_SEG2 2U
#define MOTOR_PROFILE_PMAX 12.5f
#define MOTOR_PROFILE_VMAX 10.0f
#define MOTOR_PROFILE_TMAX 28.0f
#define MOTOR_PROFILE_WORKING_VMAX 10.0f
#define MOTOR_PROFILE_WORKING_TMAX 23.5f
#endif
static inline unsigned char MotorProfile_IsFaultState(unsigned char state)
{
#if H7DM_DM_J10422P
  return (unsigned char)(state != 0U && state != 1U);
#else
  return (unsigned char)(state >= 8U);
#endif
}
static inline unsigned char MotorProfile_MappingMatches(float p, float v, float t)
{
  /* These comparisons also reject NaN and infinity. Accept vendor float rounding,
   * then use the exact readback values for both command and feedback scaling. */
  return (unsigned char)(p >= 12.565f && p <= 12.567f &&
                         v >= 19.999f && v <= 20.001f &&
                         t >= 499.99f && t <= 500.01f);
}
#endif
