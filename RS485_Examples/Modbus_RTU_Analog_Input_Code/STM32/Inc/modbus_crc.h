/**
  ******************************************************************************
  * @file           : app.h
  * @brief          : Header for crc.c file.
  ******************************************************************************
  */
#ifndef __MODBUS_CRC_H__
#define __MODBUS_CRC_H__

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>

/* Exported functions --------------------------------------------------------*/
uint16_t ModbusCRC_CheckTable(uint8_t *ptr, uint16_t len);
uint16_t ModbusCRC_CheckTableAbs(uint8_t *ptr, uint16_t len);
uint16_t ModbusCRC_Calc(uint8_t *ptr, uint16_t len);

uint32_t STM32CRC_IntCalc(uint32_t *ptr, int len);
uint32_t STM32CRC_CharCalc(uint8_t *p, uint32_t len);

#endif /* __CRC_H__ */
